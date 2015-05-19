using System.Text.Json.Serialization;

namespace ArtifactLens.Runtime;

/// <summary>
/// A single node in the provenance graph. Mirrors the Python
/// <c>artifactlens.model.Artifact</c> value object.
/// </summary>
public sealed record Artifact
{
    [JsonPropertyName("id")]
    public string Id { get; init; } = string.Empty;

    [JsonPropertyName("kind")]
    public string Kind { get; init; } = "unknown";

    [JsonPropertyName("label")]
    public string Label { get; init; } = string.Empty;

    [JsonPropertyName("content_hash")]
    public string? ContentHash { get; init; }

    [JsonPropertyName("produced_by")]
    public string? ProducedBy { get; init; }

    [JsonPropertyName("created_at")]
    public string? CreatedAt { get; init; }

    [JsonIgnore]
    public bool IsVerified => !string.IsNullOrEmpty(ContentHash);
}

/// <summary>
/// A directed transformation edge. Mirrors the Python
/// <c>artifactlens.model.Transformation</c> value object.
/// </summary>
public sealed record Transformation
{
    [JsonPropertyName("id")]
    public string Id { get; init; } = string.Empty;

    [JsonPropertyName("op")]
    public string Op { get; init; } = "derive";

    [JsonPropertyName("inputs")]
    public List<string> Inputs { get; init; } = new();

    [JsonPropertyName("outputs")]
    public List<string> Outputs { get; init; } = new();

    [JsonPropertyName("agent")]
    public string? Agent { get; init; }

    [JsonPropertyName("confidence")]
    public double? Confidence { get; init; }

