package responses
import ("reflect"; "testing")
func TestObserveResponseIntegerTypes(t *testing.T) {
 for _, value := range []interface{}{Genre{},ArtistID3{},AlbumID3{},Child{},NowPlayingEntry{},Playlist{},Share{},User{},Directory{},Error{}} {
  typ:=reflect.TypeOf(value);for i:=0;i<typ.NumField();i++ {f:=typ.Field(i);if f.Type.Kind()==reflect.Int || (f.Type.Kind()==reflect.Slice && f.Type.Elem().Kind()==reflect.Int){t.Logf("Original %s.%s=%s",typ.Name(),f.Name,f.Type)}}
 }
}
