/**
 * Parity checker for the canonical book format.
 *
 * Reads `R|id|band|balance` and `F|id|op|inputs|outputs` lines, validates the
 * references, and prints the weighted depth with the FNV-1a 64 fingerprint
 * every other port must agree on.
 */

import { readFileSync } from "node:fs";

const MICRO = 1_000_000n;
const THIN_FLOOR = 250n * MICRO;
const FNV_OFFSET = 0xcbf29ce484222325n;
const FNV_PRIME = 0x100000001b3n;
const MASK = 0xffffffffffffffffn;

interface Reserve {
  id: string;
  band: string;
  balance: bigint;
}

interface Flow {
  id: string;
  op: string;
  inputs: string[];
  outputs: string[];
}

function weightMicro(band: string): bigint {
  switch (band) {
    case "buffer":
      return 800_000n;
    case "edge":
      return 450_000n;
    case "sink":
      return 200_000n;
    default:
      return MICRO;
  }
}

function normaliseBand(band: string): string {
  return ["seed", "core", "buffer", "edge", "sink"].includes(band) ? band : "core";
}

function splitList(field: string): string[] {
  return field.split(",").filter((part) => part.length > 0);
}

function parse(text: string): { reserves: Reserve[]; flows: Flow[] } {
  const reserves = new Map<string, Reserve>();
  const flows = new Map<string, Flow>();

  text.split("\n").forEach((raw, index) => {
    const line = raw.trim();
    if (line === "" || line.startsWith("#")) return;
    const fields = line.split("|");
    const number = index + 1;

    if (fields[0] === "R") {
      if (fields.length !== 4) throw new Error(`line ${number}: reserve needs 4 fields`);
      const id = fields[1];
      if (reserves.has(id)) throw new Error(`line ${number}: duplicate reserve ${id}`);
      reserves.set(id, { id, band: normaliseBand(fields[2]), balance: BigInt(fields[3]) });
      return;
    }

    if (fields[0] === "F") {
      if (fields.length !== 5) throw new Error(`line ${number}: flow needs 5 fields`);
      const id = fields[1];
      if (flows.has(id)) throw new Error(`line ${number}: duplicate flow ${id}`);
      const outputs = splitList(fields[4]);
      if (outputs.length === 0) throw new Error(`line ${number}: flow ${id} credits nothing`);
      flows.set(id, { id, op: fields[2] || "derive", inputs: splitList(fields[3]), outputs });
      return;
    }

    throw new Error(`line ${number}: unknown record ${fields[0]}`);
  });

  for (const flow of flows.values()) {
    for (const ref of [...flow.inputs, ...flow.outputs]) {
      if (!reserves.has(ref)) throw new Error(`flow ${flow.id}: unknown reserve ${ref}`);
    }
  }

  const byId = <T extends { id: string }>(a: T, b: T) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
  return {
    reserves: [...reserves.values()].sort(byId),
    flows: [...flows.values()].sort(byId),
  };
}

function fingerprint(reserves: Reserve[], flows: Flow[]): string {
  const lines = reserves.map((r) => `R|${r.id}|${r.band}|${r.balance}`);
  for (const flow of flows) {
    const ins = [...flow.inputs].sort();
    const outs = [...flow.outputs].sort();
    lines.push(`F|${flow.id}|${flow.op}|${ins.join(",")}|${outs.join(",")}`);
  }

  const payload = `${lines.join("\n")}\n`;
  let hash = FNV_OFFSET;
  for (const byte of Buffer.from(payload, "utf8")) {
    hash = (hash ^ BigInt(byte)) & MASK;
    hash = (hash * FNV_PRIME) & MASK;
  }
  return hash.toString(16).padStart(16, "0");
}

function main(): void {
  const path = process.argv[2];
  if (!path) {
    console.error("usage: parity <book.txt>");
    process.exit(2);
  }

  let parsed: { reserves: Reserve[]; flows: Flow[] };
  try {
    parsed = parse(readFileSync(path, "utf8"));
  } catch (error) {
    console.error(`error: ${(error as Error).message}`);
    process.exit(3);
  }

  const { reserves, flows } = parsed;
  let raw = 0n;
  let depth = 0n;
  let thin = 0;
  for (const reserve of reserves) {
    raw += reserve.balance;
    depth += (reserve.balance * weightMicro(reserve.band)) / MICRO;
    if (reserve.balance > 0n && reserve.balance < THIN_FLOOR) thin += 1;
  }

  const debited = new Set<string>();
  for (const flow of flows) {
    if (flow.inputs.length === 0) continue;
    for (const out of flow.outputs) debited.add(out);
  }
  const origins = reserves.filter((r) => !debited.has(r.id)).map((r) => r.id);
  const score = raw > 0n ? Number(depth) / Number(raw) : 0;

  console.log(`reserves ${reserves.length}`);
  console.log(`flows ${flows.length}`);
  console.log(`raw ${raw}`);
  console.log(`depth ${depth}`);
  console.log(`score ${score.toFixed(4)}`);
  console.log(`thin ${thin}`);
  console.log(`origins ${origins.join(",")}`);
  console.log(`fingerprint ${fingerprint(reserves, flows)}`);
}

main();
