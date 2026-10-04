package firestore

import (
	"bytes"
	fs "cloud.google.com/go/firestore"
	"context"
	"github.com/golang/protobuf/proto"
	ts "github.com/golang/protobuf/ptypes/timestamp"
	"github.com/gravitational/teleport/lib/backend"
	"github.com/jonboulle/clockwork"
	"google.golang.org/api/option"
	pb "google.golang.org/genproto/googleapis/firestore/v1"
	"google.golang.org/grpc"
	"io"
	"net"
	"sync"
	"testing"
	"time"
)

type binaryTaskServer struct {
	pb.FirestoreServer
	mu   sync.Mutex
	docs map[string]*pb.Document
}

func (s *binaryTaskServer) Commit(ctx context.Context, req *pb.CommitRequest) (*pb.CommitResponse, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	now := &ts.Timestamp{Seconds: time.Now().Unix()}
	out := &pb.CommitResponse{CommitTime: now}
	for _, w := range req.Writes {
		d := w.GetUpdate()
		if d == nil {
			return nil, io.ErrUnexpectedEOF
		}
		if _, err := proto.Marshal(d); err != nil {
			return nil, err
		}
		d = proto.Clone(d).(*pb.Document)
		d.UpdateTime = now
		d.CreateTime = now
		s.docs[d.Name] = d
		out.WriteResults = append(out.WriteResults, &pb.WriteResult{UpdateTime: now})
	}
	return out, nil
}
func (s *binaryTaskServer) BatchGetDocuments(req *pb.BatchGetDocumentsRequest, stream pb.Firestore_BatchGetDocumentsServer) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	for _, name := range req.Documents {
		if d, ok := s.docs[name]; ok {
			if err := stream.Send(&pb.BatchGetDocumentsResponse{Result: &pb.BatchGetDocumentsResponse_Found{Found: d}}); err != nil {
				return err
			}
		} else {
			if err := stream.Send(&pb.BatchGetDocumentsResponse{Result: &pb.BatchGetDocumentsResponse_Missing{Missing: name}}); err != nil {
				return err
			}
		}
	}
	return nil
}
func TestBinaryFirestoreTask(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()
	lis, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	srv := grpc.NewServer()
	state := &binaryTaskServer{docs: map[string]*pb.Document{}}
	pb.RegisterFirestoreServer(srv, state)
	go srv.Serve(lis)
	defer srv.Stop()
	defer lis.Close()
	conn, err := grpc.DialContext(ctx, lis.Addr().String(), grpc.WithInsecure(), grpc.WithBlock())
	if err != nil {
		t.Fatal(err)
	}
	defer conn.Close()
	client, err := fs.NewClient(ctx, "binary-task", option.WithGRPCConn(conn), option.WithoutAuthentication())
	if err != nil {
		t.Fatal(err)
	}
	defer client.Close()
	b := &FirestoreBackend{svc: client, clock: clockwork.NewRealClock()}
	b.CollectionName = "task"
	key := []byte("binary")
	values := [][]byte{{0xff, 0xfe, 0x00, 0x80}, {0x00, 0xff, 0x81}, {0x82, 0xfe}, {0x83, 0xff}}
	checks := func(want []byte) {
		got, err := b.Get(ctx, key)
		if err != nil {
			t.Fatal(err)
		}
		if !bytes.Equal(got.Value, want) {
			t.Fatalf("roundtrip: %x != %x", got.Value, want)
		}
		state.mu.Lock()
		defer state.mu.Unlock()
		for _, d := range state.docs {
			if d.Fields["key"].GetStringValue() == "binary" {
				if v, ok := d.Fields["value"].ValueType.(*pb.Value_BytesValue); !ok || !bytes.Equal(v.BytesValue, want) {
					t.Fatalf("not native bytes: %+v", d.Fields["value"])
				}
			}
		}
		t.Logf("native Firestore BytesValue roundtrip %x", got.Value)
	}
	if _, err = b.Create(ctx, backend.Item{Key: key, Value: values[0]}); err != nil {
		t.Fatal(err)
	}
	checks(values[0])
	if _, err = b.Put(ctx, backend.Item{Key: key, Value: values[1]}); err != nil {
		t.Fatal(err)
	}
	checks(values[1])
	if _, err = b.Update(ctx, backend.Item{Key: key, Value: values[2]}); err != nil {
		t.Fatal(err)
	}
	checks(values[2])
	if _, err = b.CompareAndSwap(ctx, backend.Item{Key: key, Value: values[2]}, backend.Item{Key: key, Value: values[3]}); err != nil {
		t.Fatal(err)
	}
	checks(values[3])
	if _, err = b.CompareAndSwap(ctx, backend.Item{Key: key, Value: []byte("mismatch")}, backend.Item{Key: key, Value: []byte("bad")}); err == nil {
		t.Fatal("mismatch should fail")
	}
	checks(values[3])
	legacyName := client.Collection("task").Doc(b.keyToDocumentID([]byte("legacy"))).Path
	state.mu.Lock()
	state.docs[legacyName] = &pb.Document{Name: legacyName, CreateTime: &ts.Timestamp{Seconds: time.Now().Unix()}, UpdateTime: &ts.Timestamp{Seconds: time.Now().Unix()}, Fields: map[string]*pb.Value{
		"key": {ValueType: &pb.Value_StringValue{StringValue: "legacy"}}, "value": {ValueType: &pb.Value_StringValue{StringValue: "old-format"}},
		"id": {ValueType: &pb.Value_IntegerValue{IntegerValue: 42}}, "expires": {ValueType: &pb.Value_IntegerValue{IntegerValue: time.Now().Add(time.Hour).Unix()}}}}
	state.mu.Unlock()
	got, err := b.Get(ctx, []byte("legacy"))
	if err != nil {
		t.Fatal(err)
	}
	if string(got.Value) != "old-format" || got.ID != 42 || got.Expires.IsZero() {
		t.Fatalf("legacy metadata lost: %+v", got)
	}
	t.Logf("legacy string returned %q id=%d expires-preserved=true", got.Value, got.ID)
	snap, err := client.Collection("task").Doc(b.keyToDocumentID([]byte("legacy"))).Get(ctx)
	if err != nil {
		t.Fatal(err)
	}
	var current record
	if err = decodeRecord(snap, &current); err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(current.Value, []byte("old-format")) {
		t.Fatal("legacy fallback failed")
	}
}
