package main

import "testing"

const book = "R|a|seed|1000000\nR|b|core|500000\nF|f|deposit|a|b\n"

func TestParsesAndFingerprints(t *testing.T) {
	reserves, flows, err := parse(book)
	if err != nil {
		t.Fatalf("parse: %v", err)
	}
	if len(reserves) != 2 || len(flows) != 1 {
		t.Fatalf("got %d reserves %d flows", len(reserves), len(flows))
	}
	if len(fingerprint(reserves, flows)) != 16 {
		t.Fatal("fingerprint width")
	}
}

func TestRejectsUnknownReference(t *testing.T) {
	if _, _, err := parse("R|a|core|1\nF|f|deposit|a|ghost\n"); err == nil {
		t.Fatal("expected error")
	}
}

func TestRejectsEmptyOutputs(t *testing.T) {
	if _, _, err := parse("R|a|core|1\nF|f|deposit|a|\n"); err == nil {
		t.Fatal("expected error")
	}
}
