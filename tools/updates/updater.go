// Boufbowl desktop bootstrap: signed full-package updates with offline fallback.
package main

import (
	"crypto/ed25519"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"time"
)

var publicKey string // Set by the package builder, never fetched from the server.
type config struct {
	Version  string `json:"version"`
	Manifest string `json:"manifest"`
	Platform string `json:"platform"`
}
type artifact struct {
	Version string `json:"version"`
	URL     string `json:"url"`
	SHA256  string `json:"sha256"`
	Bytes   int64  `json:"bytes"`
}
type manifest struct {
	Schema    int                 `json:"schema"`
	Platforms map[string]artifact `json:"platforms"`
}
type envelope struct {
	Payload   string `json:"payload"`
	Signature string `json:"signature"`
}

func version(s string) ([3]int, error) {
	var v [3]int
	p := strings.Split(s, ".")
	if len(p) != 3 {
		return v, errors.New("version")
	}
	for i, n := range p {
		x, e := strconv.Atoi(n)
		if e != nil || x < 0 || x > 999 {
			return v, errors.New("version")
		}
		v[i] = x
	}
	return v, nil
}
func newer(a, b string) bool {
	x, e := version(a)
	if e != nil {
		return false
	}
	y, e := version(b)
	if e != nil {
		return false
	}
	for i := range x {
		if x[i] != y[i] {
			return x[i] > y[i]
		}
	}
	return false
}
func authenticated(data []byte) (manifest, error) {
	var env envelope
	var m manifest
	if err := json.Unmarshal(data, &env); err != nil {
		return m, err
	}
	key, e := hex.DecodeString(publicKey)
	if e != nil || len(key) != ed25519.PublicKeySize {
		return m, errors.New("invalid trusted key")
	}
	sig, e := base64.StdEncoding.DecodeString(env.Signature)
	if e != nil || !ed25519.Verify(key, []byte(env.Payload), sig) {
		return m, errors.New("invalid release signature")
	}
	if e = json.Unmarshal([]byte(env.Payload), &m); e != nil {
		return m, e
	}
	if m.Schema != 1 {
		return m, errors.New("unsupported release manifest")
	}
	return m, nil
}
func sameOrigin(base, target string) bool {
	a, e := url.Parse(base)
	if e != nil {
		return false
	}
	b, e := url.Parse(target)
	return e == nil && a.Scheme == "https" && b.Scheme == "https" && a.Host == b.Host && b.User == nil
}
func client(base string, timeout time.Duration) *http.Client {
	return &http.Client{Timeout: timeout, CheckRedirect: func(req *http.Request, via []*http.Request) error {
		if len(via) > 5 || !sameOrigin(base, req.URL.String()) {
			return errors.New("unsafe redirect")
		}
		return nil
	}}
}
func get(base, target string, limit int64, timeout time.Duration) ([]byte, error) {
	if !sameOrigin(base, target) {
		return nil, errors.New("unsafe update URL")
	}
	r, e := client(base, timeout).Get(target)
	if e != nil {
		return nil, e
	}
	defer r.Body.Close()
	if r.StatusCode != 200 {
		return nil, fmt.Errorf("HTTP %d", r.StatusCode)
	}
	b, e := io.ReadAll(io.LimitReader(r.Body, limit+1))
	if e == nil && int64(len(b)) > limit {
		e = errors.New("download too large")
	}
	return b, e
}
func checksum(file, expected string, size int64) bool {
	f, e := os.Open(file)
	if e != nil {
		return false
	}
	defer f.Close()
	h := sha256.New()
	n, e := io.Copy(h, f)
	return e == nil && n == size && hex.EncodeToString(h.Sum(nil)) == expected
}
func fetchPackage(cfg config, a artifact, cache string) (string, error) {
	if _, e := version(a.Version); e != nil {
		return "", e
	}
	hash, e := hex.DecodeString(a.SHA256)
	if e != nil || len(hash) != 32 || a.Bytes <= 0 || a.Bytes > 1024*1024*1024 {
		return "", errors.New("invalid package metadata")
	}
	extension := ".run"
	if cfg.Platform == "windows" {
		extension = ".exe"
	}
	target := filepath.Join(cache, a.SHA256+extension)
	if checksum(target, a.SHA256, a.Bytes) {
		return target, nil
	}
	if !sameOrigin(cfg.Manifest, a.URL) {
		return "", errors.New("unsafe package URL")
	}
	r, e := client(cfg.Manifest, 3*time.Minute).Get(a.URL)
	if e != nil {
		return "", e
	}
	defer r.Body.Close()
	if r.StatusCode != 200 {
		return "", fmt.Errorf("HTTP %d", r.StatusCode)
	}
	f, e := os.CreateTemp(cache, ".download-*")
	if e != nil {
		return "", e
	}
	defer os.Remove(f.Name())
	h := sha256.New()
	n, e := io.Copy(io.MultiWriter(f, h), io.LimitReader(r.Body, a.Bytes+1))
	closeErr := f.Close()
	if e != nil {
		return "", e
	}
	if closeErr != nil {
		return "", closeErr
	}
	if n != a.Bytes || hex.EncodeToString(h.Sum(nil)) != a.SHA256 {
		return "", errors.New("package checksum mismatch")
	}
	if e = os.Chmod(f.Name(), 0700); e != nil {
		return "", e
	}
	if e = os.Rename(f.Name(), target); e != nil {
		return "", e
	}
	return target, nil
}
func save(file string, data []byte) error {
	f, e := os.CreateTemp(filepath.Dir(file), ".manifest-*")
	if e != nil {
		return e
	}
	defer os.Remove(f.Name())
	if _, e = f.Write(data); e != nil {
		f.Close()
		return e
	}
	if e = f.Close(); e != nil {
		return e
	}
	if runtime.GOOS == "windows" {
		os.Remove(file)
	}
	return os.Rename(f.Name(), file)
}
func update(cfg config) (string, error) {
	home, e := os.UserCacheDir()
	if e != nil {
		return "", e
	}
	cache := filepath.Join(home, "boufbowl", "updates", cfg.Platform)
	if e = os.MkdirAll(cache, 0700); e != nil {
		return "", e
	}
	cached := filepath.Join(cache, "current.json")
	saved, _ := os.ReadFile(cached)
	previous, previousErr := authenticated(saved)
	checkURL, _ := url.Parse(cfg.Manifest)
	q := checkURL.Query()
	q.Set("check", strconv.FormatInt(time.Now().UnixNano(), 10))
	checkURL.RawQuery = q.Encode()
	data, e := get(cfg.Manifest, checkURL.String(), 128*1024, 5*time.Second)
	if e == nil {
		m, err := authenticated(data)
		if err == nil && previousErr == nil && newer(previous.Platforms[cfg.Platform].Version, m.Platforms[cfg.Platform].Version) {
			data = saved
			m = previous
		}
		if err == nil {
			a, ok := m.Platforms[cfg.Platform]
			if ok && newer(a.Version, cfg.Version) {
				target, err := fetchPackage(cfg, a, cache)
				if err == nil {
					save(cached, data)
					return target, nil
				}
				fmt.Fprintln(os.Stderr, "Mise à jour indisponible :", err)
			}
		} else {
			fmt.Fprintln(os.Stderr, "Mise à jour ignorée :", err)
		}
	}
	data, e = os.ReadFile(cached)
	if e != nil {
		return "", nil
	}
	m, e := authenticated(data)
	if e != nil {
		return "", nil
	}
	a, ok := m.Platforms[cfg.Platform]
	if !ok || !newer(a.Version, cfg.Version) {
		return "", nil
	}
	// Offline fallback uses only an already verified, complete cached package.
	extension := ".run"
	if cfg.Platform == "windows" {
		extension = ".exe"
	}
	target := filepath.Join(cache, a.SHA256+extension)
	if len(a.SHA256) == 64 && checksum(target, a.SHA256, a.Bytes) {
		return target, nil
	}
	return "", nil
}
func run() error {
	exe, e := os.Executable()
	if e != nil {
		return e
	}
	root := filepath.Dir(exe)
	data, e := os.ReadFile(filepath.Join(root, "update-client.json"))
	if e != nil {
		return e
	}
	var cfg config
	if e = json.Unmarshal(data, &cfg); e != nil {
		return e
	}
	expected := "linux"
	if runtime.GOOS == "windows" {
		expected = "windows"
	}
	if cfg.Platform != expected {
		return errors.New("updater platform mismatch")
	}
	next, e := update(cfg)
	if e != nil {
		fmt.Fprintln(os.Stderr, "Vérification des mises à jour indisponible :", e)
	}
	var cmd *exec.Cmd
	if next != "" {
		cmd = exec.Command(next)
	} else if runtime.GOOS == "windows" {
		cmd = exec.Command("cmd.exe", "/d", "/c", "Jouer-game.cmd")
		cmd.Dir = root
	} else {
		cmd = exec.Command("sh", "./jouer-game.sh")
		cmd.Dir = root
	}
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin
	return cmd.Run()
}
func main() {
	if e := run(); e != nil {
		fmt.Fprintln(os.Stderr, "Impossible de lancer Boufbowl :", e)
		os.Exit(1)
	}
}
