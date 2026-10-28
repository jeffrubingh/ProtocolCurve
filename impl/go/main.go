// Parity checker for the canonical book format.
//
// Reads R|id|band|balance and F|id|op|inputs|outputs lines, validates the
// references, and prints the weighted depth with the FNV-1a 64 fingerprint
// every other port must agree on.
package main

import (
	"bufio"
	"fmt"
	"os"
	"sort"
	"strconv"
	"strings"
)

const (
	micro     int64  = 1_000_000
	floor     int64  = 250 * micro
	fnvOffset uint64 = 0xCBF29CE484222325
	fnvPrime  uint64 = 0x100000001B3
)

type reserve struct {
	id      string
	band    string
	balance int64
}

type flow struct {
	id      string
	op      string
	inputs  []string
	outputs []string
}

func weightMicro(band string) int64 {
	switch band {
	case "buffer":
		return 800_000
	case "edge":
		return 450_000
	case "sink":
		return 200_000
	default:
		return micro
	}
}

func normaliseBand(band string) string {
	switch band {
	case "seed", "core", "buffer", "edge", "sink":
		return band
	default:
		return "core"
	}
}

func splitList(field string) []string {
	out := []string{}
	for _, part := range strings.Split(field, ",") {
		if part != "" {
			out = append(out, part)
		}
	}
	return out
}

func parse(text string) ([]reserve, []flow, error) {
	reserves := map[string]reserve{}
	flows := map[string]flow{}
	scanner := bufio.NewScanner(strings.NewReader(text))
	line := 0

	for scanner.Scan() {
		line++
		trimmed := strings.TrimSpace(scanner.Text())
		if trimmed == "" || strings.HasPrefix(trimmed, "#") {
			continue
		}
		fields := strings.Split(trimmed, "|")
		switch fields[0] {
		case "R":
			if len(fields) != 4 {
				return nil, nil, fmt.Errorf("line %d: reserve needs 4 fields", line)
			}
			if _, seen := reserves[fields[1]]; seen {
				return nil, nil, fmt.Errorf("line %d: duplicate reserve %s", line, fields[1])
			}
			balance, err := strconv.ParseInt(fields[3], 10, 64)
			if err != nil {
				return nil, nil, fmt.Errorf("line %d: bad balance", line)
			}
			reserves[fields[1]] = reserve{id: fields[1], band: normaliseBand(fields[2]), balance: balance}
		case "F":
			if len(fields) != 5 {
				return nil, nil, fmt.Errorf("line %d: flow needs 5 fields", line)
			}
			if _, seen := flows[fields[1]]; seen {
				return nil, nil, fmt.Errorf("line %d: duplicate flow %s", line, fields[1])
			}
			outputs := splitList(fields[4])
			if len(outputs) == 0 {
				return nil, nil, fmt.Errorf("line %d: flow %s credits nothing", line, fields[1])
			}
			op := fields[2]
			if op == "" {
				op = "derive"
			}
			flows[fields[1]] = flow{id: fields[1], op: op, inputs: splitList(fields[3]), outputs: outputs}
		default:
			return nil, nil, fmt.Errorf("line %d: unknown record %s", line, fields[0])
		}
	}

	for _, f := range flows {
		for _, ref := range append(append([]string{}, f.inputs...), f.outputs...) {
			if _, ok := reserves[ref]; !ok {
				return nil, nil, fmt.Errorf("flow %s: unknown reserve %s", f.id, ref)
			}
		}
	}

	ordered := make([]reserve, 0, len(reserves))
	for _, r := range reserves {
		ordered = append(ordered, r)
	}
	sort.Slice(ordered, func(i, j int) bool { return ordered[i].id < ordered[j].id })

	orderedFlows := make([]flow, 0, len(flows))
	for _, f := range flows {
		orderedFlows = append(orderedFlows, f)
	}
	sort.Slice(orderedFlows, func(i, j int) bool { return orderedFlows[i].id < orderedFlows[j].id })

	return ordered, orderedFlows, nil
}

func fingerprint(reserves []reserve, flows []flow) string {
	lines := make([]string, 0, len(reserves)+len(flows))
	for _, r := range reserves {
		lines = append(lines, fmt.Sprintf("R|%s|%s|%d", r.id, r.band, r.balance))
	}
	for _, f := range flows {
		ins := append([]string{}, f.inputs...)
		outs := append([]string{}, f.outputs...)
		sort.Strings(ins)
		sort.Strings(outs)
		lines = append(lines, fmt.Sprintf("F|%s|%s|%s|%s", f.id, f.op, strings.Join(ins, ","), strings.Join(outs, ",")))
	}
	payload := strings.Join(lines, "\n") + "\n"
	hash := uint64(fnvOffset)
	for i := 0; i < len(payload); i++ {
		hash ^= uint64(payload[i])
		hash *= fnvPrime
	}
	return fmt.Sprintf("%016x", hash)
}

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: parity <book.txt>")
		os.Exit(2)
	}
	blob, err := os.ReadFile(os.Args[1])
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		os.Exit(1)
	}
	reserves, flows, err := parse(string(blob))
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		os.Exit(3)
	}

	var raw, depth int64
	thin := 0
	for _, r := range reserves {
		raw += r.balance
		depth += r.balance * weightMicro(r.band) / micro
		if r.balance > 0 && r.balance < floor {
			thin++
		}
	}
	debited := map[string]bool{}
	for _, f := range flows {
		if len(f.inputs) == 0 {
			continue
		}
		for _, out := range f.outputs {
			debited[out] = true
		}
	}
	origins := []string{}
	for _, r := range reserves {
		if !debited[r.id] {
			origins = append(origins, r.id)
		}
	}

	score := 0.0
	if raw > 0 {
		score = float64(depth) / float64(raw)
	}

	fmt.Printf("reserves %d\n", len(reserves))
	fmt.Printf("flows %d\n", len(flows))
	fmt.Printf("raw %d\n", raw)
	fmt.Printf("depth %d\n", depth)
	fmt.Printf("score %.4f\n", score)
	fmt.Printf("thin %d\n", thin)
	fmt.Printf("origins %s\n", strings.Join(origins, ","))
	fmt.Printf("fingerprint %s\n", fingerprint(reserves, flows))
}
