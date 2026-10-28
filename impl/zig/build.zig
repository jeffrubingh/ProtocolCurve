const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    const exe = b.addExecutable(.{
        .name = "parity",
        .root_source_file = b.path("src/main.zig"),
        .target = target,
        .optimize = optimize,
    });
    b.installArtifact(exe);

    const run = b.addRunArtifact(exe);
    if (b.args) |args| run.addArgs(args);
    b.step("run", "run the parity check").dependOn(&run.step);

    const tests = b.addTest(.{ .root_source_file = b.path("src/main.zig"), .target = target });
    b.step("test", "run unit tests").dependOn(&b.addRunArtifact(tests).step);
}
