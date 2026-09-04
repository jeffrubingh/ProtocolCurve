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

    [JsonIgnore]
    public double EffectiveConfidence =>
        Confidence is null ? 1.0 : Math.Clamp(Confidence.Value, 0.0, 1.0);
}

/// <summary>
/// A combined graph document: the on-disk JSON shape shared with the Python
/// package.
/// </summary>
public sealed record GraphDocument
{
    [JsonPropertyName("artifacts")]
    public List<Artifact> Artifacts { get; init; } = new();

    [JsonPropertyName("transformations")]
    public List<Transformation> Transformations { get; init; } = new();
}

/// <summary>Provenance coverage metrics, byte-for-byte compatible with Python.</summary>
public sealed record CoverageReport
{
    public int TotalArtifacts { get; init; }
    public int ConnectedArtifacts { get; init; }
    public int VerifiedArtifacts { get; init; }
    public int RootedArtifacts { get; init; }
    public List<string> OrphanIds { get; init; } = new();
    public List<string> DanglingIds { get; init; } = new();
    public double CoverageScore { get; init; }
}
