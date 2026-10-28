//! Parity checker for the canonical book format.
//!
//! Reads `R|id|band|balance` and `F|id|op|inputs|outputs` lines, validates the
//! references, and prints the weighted depth with the FNV-1a 64 fingerprint
//! every other port must agree on.

const std = @import("std");

const micro: i64 = 1_000_000;
const thin_floor: i64 = 250 * micro;
const fnv_offset: u64 = 0xCBF29CE484222325;
const fnv_prime: u64 = 0x100000001B3;

const Reserve = struct {
    id: []const u8,
    band: []const u8,
    balance: i64,
};

const Flow = struct {
    id: []const u8,
    op: []const u8,
    inputs: [][]const u8,
    outputs: [][]const u8,
};

fn weightMicro(band: []const u8) i64 {
    if (std.mem.eql(u8, band, "buffer")) return 800_000;
    if (std.mem.eql(u8, band, "edge")) return 450_000;
    if (std.mem.eql(u8, band, "sink")) return 200_000;
    return micro;
}

fn normaliseBand(band: []const u8) []const u8 {
    const known = [_][]const u8{ "seed", "core", "buffer", "edge", "sink" };
    for (known) |item| {
        if (std.mem.eql(u8, band, item)) return band;
    }
    return "core";
}

fn splitList(allocator: std.mem.Allocator, field: []const u8) ![][]const u8 {
    var list = std.ArrayList([]const u8).init(allocator);
    var it = std.mem.splitScalar(u8, field, ',');
    while (it.next()) |part| {
        if (part.len > 0) try list.append(part);
    }
    return list.toOwnedSlice();
}

fn lessThanId(comptime T: type) fn (void, T, T) bool {
    return struct {
        fn inner(_: void, a: T, b: T) bool {
            return std.mem.lessThan(u8, a.id, b.id);
        }
    }.inner;
}

fn fingerprint(allocator: std.mem.Allocator, reserves: []Reserve, flows: []Flow) ![]u8 {
    var payload = std.ArrayList(u8).init(allocator);
    const writer = payload.writer();
    for (reserves) |reserve| {
        try writer.print("R|{s}|{s}|{d}\n", .{ reserve.id, reserve.band, reserve.balance });
    }
    for (flows) |flow| {
        const ins = try allocator.dupe([]const u8, flow.inputs);
        const outs = try allocator.dupe([]const u8, flow.outputs);
        std.mem.sort([]const u8, ins, {}, struct {
            fn cmp(_: void, a: []const u8, b: []const u8) bool {
                return std.mem.lessThan(u8, a, b);
            }
        }.cmp);
        std.mem.sort([]const u8, outs, {}, struct {
            fn cmp(_: void, a: []const u8, b: []const u8) bool {
                return std.mem.lessThan(u8, a, b);
            }
        }.cmp);
        try writer.print("F|{s}|{s}|{s}|{s}\n", .{
            flow.id,
            flow.op,
            try std.mem.join(allocator, ",", ins),
            try std.mem.join(allocator, ",", outs),
        });
    }

    var hash: u64 = fnv_offset;
    for (payload.items) |byte| {
        hash ^= byte;
        hash *%= fnv_prime;
    }
    return std.fmt.allocPrint(allocator, "{x:0>16}", .{hash});
}

pub fn main() !u8 {
    var arena = std.heap.ArenaAllocator.init(std.heap.page_allocator);
    defer arena.deinit();
    const allocator = arena.allocator();

    var args = try std.process.argsWithAllocator(allocator);
    _ = args.next();
    const path = args.next() orelse {
        std.debug.print("usage: parity <book.txt>\n", .{});
        return 2;
    };

    const text = std.fs.cwd().readFileAlloc(allocator, path, 8 * 1024 * 1024) catch {
        std.debug.print("error: cannot read {s}\n", .{path});
        return 1;
    };

    var reserves = std.ArrayList(Reserve).init(allocator);
    var flows = std.ArrayList(Flow).init(allocator);

    var lines = std.mem.splitScalar(u8, text, '\n');
    var number: usize = 0;
    while (lines.next()) |raw| {
        number += 1;
        const line = std.mem.trim(u8, raw, " \r\t");
        if (line.len == 0 or line[0] == '#') continue;

        var fields = std.mem.splitScalar(u8, line, '|');
        const tag = fields.next() orelse continue;
        if (std.mem.eql(u8, tag, "R")) {
            const id = fields.next() orelse return bad(number, "reserve needs 4 fields");
            const band = fields.next() orelse return bad(number, "reserve needs 4 fields");
            const balance_text = fields.next() orelse return bad(number, "reserve needs 4 fields");
            const balance = std.fmt.parseInt(i64, balance_text, 10) catch return bad(number, "bad balance");
            reserves.append(.{ .id = id, .band = normaliseBand(band), .balance = balance }) catch unreachable;
        } else if (std.mem.eql(u8, tag, "F")) {
            const id = fields.next() orelse return bad(number, "flow needs 5 fields");
            const op = fields.next() orelse return bad(number, "flow needs 5 fields");
            const inputs_text = fields.next() orelse return bad(number, "flow needs 5 fields");
            const outputs_text = fields.next() orelse return bad(number, "flow needs 5 fields");
            const outputs = try splitList(allocator, outputs_text);
            if (outputs.len == 0) return bad(number, "flow credits nothing");
            flows.append(.{
                .id = id,
                .op = if (op.len == 0) "derive" else op,
                .inputs = try splitList(allocator, inputs_text),
                .outputs = outputs,
            }) catch unreachable;
        } else {
            return bad(number, "unknown record");
        }
    }

    for (flows.items) |flow| {
        for (flow.inputs) |ref| try require(reserves.items, ref);
        for (flow.outputs) |ref| try require(reserves.items, ref);
    }

    std.mem.sort(Reserve, reserves.items, {}, lessThanId(Reserve));
    std.mem.sort(Flow, flows.items, {}, lessThanId(Flow));

    var raw_total: i64 = 0;
    var depth: i64 = 0;
    var thin: usize = 0;
    for (reserves.items) |reserve| {
        raw_total += reserve.balance;
        depth += @divTrunc(reserve.balance * weightMicro(reserve.band), micro);
        if (reserve.balance > 0 and reserve.balance < thin_floor) thin += 1;
    }

    var debited = std.StringHashMap(void).init(allocator);
    for (flows.items) |flow| {
        if (flow.inputs.len == 0) continue;
        for (flow.outputs) |out| try debited.put(out, {});
    }
    var origins = std.ArrayList([]const u8).init(allocator);
    for (reserves.items) |reserve| {
        if (!debited.contains(reserve.id)) try origins.append(reserve.id);
    }

    const stdout = std.io.getStdOut().writer();
    try stdout.print("reserves {d}\n", .{reserves.items.len});
    try stdout.print("flows {d}\n", .{flows.items.len});
    try stdout.print("raw {d}\n", .{raw_total});
    try stdout.print("depth {d}\n", .{depth});
    try stdout.print("score {d:.4}\n", .{if (raw_total > 0) @as(f64, @floatFromInt(depth)) / @as(f64, @floatFromInt(raw_total)) else 0.0});
    try stdout.print("thin {d}\n", .{thin});
    try stdout.print("origins {s}\n", .{try std.mem.join(allocator, ",", origins.items)});
    try stdout.print("fingerprint {s}\n", .{try fingerprint(allocator, reserves.items, flows.items)});
    return 0;
}

fn bad(number: usize, message: []const u8) u8 {
    std.debug.print("error: line {d}: {s}\n", .{ number, message });
    return 3;
}

fn require(reserves: []const Reserve, reference: []const u8) !void {
    for (reserves) |reserve| {
        if (std.mem.eql(u8, reserve.id, reference)) return;
    }
    std.debug.print("error: unknown reserve {s}\n", .{reference});
    return error.UnknownReserve;
}

test "fingerprint width" {
    var arena = std.heap.ArenaAllocator.init(std.testing.allocator);
    defer arena.deinit();
    const allocator = arena.allocator();
    const reserves = [_]Reserve{.{ .id = "a", .band = "core", .balance = 1 }};
    const flows = [_]Flow{.{ .id = "f", .op = "seed", .inputs = &[_][]const u8{}, .outputs = &[_][]const u8{"a"} }};
    const value = try fingerprint(allocator, &reserves, &flows);
    try std.testing.expectEqual(@as(usize, 16), value.len);
}
