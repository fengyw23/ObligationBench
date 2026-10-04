package responses

import (
 "encoding/json"
 "encoding/xml"
 "math"
 "reflect"
 "testing"
)

func TestResponseIntegerWidths(t *testing.T) {
 types := []interface{}{Error{}, Artist{}, ArtistID3{}, AlbumID3{}, Child{}, NowPlayingEntry{}, Playlist{}, Share{}, User{}, Directory{}, Genre{}, ScanStatus{}}
 changed := 0
 for _, value := range types {
  typ := reflect.TypeOf(value)
  for i:=0; i<typ.NumField(); i++ {
   f:=typ.Field(i)
   if f.Type.Kind()==reflect.Int { t.Fatalf("%s.%s remains platform int",typ.Name(),f.Name) }
   if f.Type.Kind()==reflect.Slice && f.Type.Elem().Kind()==reflect.Int { t.Fatalf("%s.%s remains []int",typ.Name(),f.Name) }
   if f.Type.Kind()==reflect.Int32 || (f.Type.Kind()==reflect.Slice && f.Type.Elem().Kind()==reflect.Int32) { changed++; t.Logf("%s.%s=%s",typ.Name(),f.Name,f.Type) }
  }
 }
 if changed != 30 { t.Fatalf("expected 30 int32 fields, got %d",changed) }
}

func TestResponseIntegerJSONXMLBoundaries(t *testing.T) {
 for _, value := range []int32{math.MinInt32, -1, 0, 1, math.MaxInt32} {
  child:=Child{Id:"test",Track:value,Year:value,Duration:value,BitRate:value,DiscNumber:value,UserRating:value,SongCount:value,Size:1<<40,PlayCount:1<<35,BookmarkPosition:1<<38}
  for _, encoding := range []string{"JSON","XML"} {
   var data []byte; var err error; var decoded Child
   if encoding=="JSON" { data,err=json.Marshal(child); if err==nil { err=json.Unmarshal(data,&decoded) } } else { data,err=xml.Marshal(child); if err==nil { err=xml.Unmarshal(data,&decoded) } }
   if err!=nil { t.Fatal(err) }; if !reflect.DeepEqual(child,decoded) { t.Fatalf("%s roundtrip %d: %+v",encoding,value,decoded) }
   t.Logf("%s roundtrip integer=%d retains explicit int64 sizes and positions",encoding,value)
  }
 }
 user:=User{Folder:[]int32{0,math.MaxInt32},MaxBitRate:320};data,err:=json.Marshal(user);if err!=nil{t.Fatal(err)};var decoded User;if err=json.Unmarshal(data,&decoded);err!=nil{t.Fatal(err)};if !reflect.DeepEqual(user,decoded){t.Fatal("user integer array roundtrip failed")}
}
