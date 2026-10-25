package main

import (
	"crypto/ed25519"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
)

func signed(t *testing.T, key ed25519.PrivateKey, m manifest) []byte {
	t.Helper()
	p, _ := json.Marshal(m)
	b, _ := json.Marshal(envelope{string(p), base64.StdEncoding.EncodeToString(ed25519.Sign(key, p))})
	return b
}
func TestVersions(t *testing.T) {
	for _, c := range []struct {
		a, b string
		want bool
	}{{"0.2.0", "0.1.9", true}, {"0.1.0", "0.1.0", false}, {"1.0.0", "0.999.999", true}, {"0.1.0", "1.0.0", false}, {"bad", "0.1.0", false}} {
		if newer(c.a, c.b) != c.want {
			t.Fatal(c)
		}
	}
}
func TestSignature(t *testing.T) {
	pub, key, _ := ed25519.GenerateKey(rand.Reader)
	publicKey = hex.EncodeToString(pub)
	b := signed(t, key, manifest{Schema: 1})
	if _, e := authenticated(b); e != nil {
		t.Fatal(e)
	}
	var env envelope
	json.Unmarshal(b, &env)
	env.Payload += " "
	bad, _ := json.Marshal(env)
	if _, e := authenticated(bad); e == nil {
		t.Fatal("accepted tampered manifest")
	}
	publicKey = hex.EncodeToString(make([]byte, 32))
	if _, e := authenticated(b); e == nil {
		t.Fatal("accepted wrong key")
	}
}
func TestUpdateCacheFallbackAndRollback(t *testing.T) {
	t.Setenv("XDG_CACHE_HOME", t.TempDir())
	pub, key, _ := ed25519.GenerateKey(rand.Reader)
	publicKey = hex.EncodeToString(pub)
	body := []byte("#!/bin/sh\necho signed-package\n")
	hash := sha256.Sum256(body)
	var response []byte
	badDownload := false
	server := httptest.NewTLSServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/updates.json" {
			w.Write(response)
		} else if badDownload {
			w.Write([]byte("truncated"))
		} else {
			w.Write(body)
		}
	}))
	defer server.Close()
	transport := http.DefaultTransport
	http.DefaultTransport = server.Client().Transport
	defer func() { http.DefaultTransport = transport }()
	cfg := config{"0.1.0", server.URL + "/updates.json", "linux"}
	a := artifact{"0.2.0", server.URL + "/package.run", hex.EncodeToString(hash[:]), int64(len(body))}
	response = signed(t, key, manifest{1, map[string]artifact{"linux": a}})
	target, e := update(cfg)
	if e != nil || target == "" || !checksum(target, a.SHA256, a.Bytes) {
		t.Fatalf("download failed: %s %v", target, e)
	}
	response = []byte("invalid manifest")
	offline, e := update(cfg)
	if e != nil || offline != target {
		t.Fatal("did not reuse authenticated cache", e)
	}
	a.Version = "0.1.1"
	response = signed(t, key, manifest{1, map[string]artifact{"linux": a}})
	rolled, e := update(cfg)
	if e != nil || rolled != target {
		t.Fatal("downgraded cached package", e)
	}
	// A higher release that fails validation must retain the last usable version.
	a.Version = "0.3.0"
	a.SHA256 = hex.EncodeToString(make([]byte, 32))
	badDownload = true
	response = signed(t, key, manifest{1, map[string]artifact{"linux": a}})
	fallback, e := update(cfg)
	if e != nil || fallback != target {
		t.Fatal("failed download replaced usable cache", e)
	}
	cached, _ := os.ReadFile(filepath.Join(filepath.Dir(target), "current.json"))
	m, e := authenticated(cached)
	if e != nil || m.Platforms["linux"].Version != "0.2.0" {
		t.Fatal("damaged cached manifest")
	}
	cfg.Version = "0.2.0"
	response = []byte("offline")
	if next, _ := update(cfg); next != "" {
		t.Fatal("cached package caused recursive relaunch")
	}
}
func TestOrigins(t *testing.T) {
	for _, target := range []string{"http://example.com/p", "https://evil.test/p", "https://user@example.com/p"} {
		if sameOrigin("https://example.com/updates.json", target) {
			t.Fatal(target)
		}
	}
}
