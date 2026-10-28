using System.Text.Json.Serialization;

namespace CurveProtocol.Runtime;

/// <summary>Bands, ordered from the quietest to the most exposed.</summary>
public static class Bands
{
    public static readonly string[] All = { "seed", "core", "buffer", "edge", "sink" };

    public static string Normalise(string? band) =>
        band is not null && Array.IndexOf(All, band) >= 0 ? band : "core";

    public static double DefaultWeight(string band) => band switch
    {
        "buffer" => 0.8,
        "edge" => 0.45,
        "sink" => 0.2,
        _ => 1.0,
    };
}

/// <summary>A single tranche in the book. Balance is integer micro-USDT.</summary>
public sealed class ReserveRecord
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = "";

    [JsonPropertyName("band")]
    public string? Band { get; set; }

    [JsonPropertyName("label")]
    public string? Label { get; set; }

    [JsonPropertyName("balance")]
    public long Balance { get; set; }

    [JsonPropertyName("epoch")]
    public long Epoch { get; set; }

    [JsonPropertyName("weight")]
    public double? Weight { get; set; }

    [JsonIgnore]
    public string NormalisedBand => Bands.Normalise(Band);

    [JsonIgnore]
    public double NormalisedWeight => Math.Clamp(Weight ?? Bands.DefaultWeight(NormalisedBand), 0.0, 1.0);

    [JsonIgnore]
    public string DisplayLabel => string.IsNullOrEmpty(Label) ? Id : Label;
}

/// <summary>A directed capital movement.</summary>
public sealed class FlowRecord
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = "";

    [JsonPropertyName("op")]
    public string Op { get; set; } = "derive";

    [JsonPropertyName("inputs")]
    public List<string> Inputs { get; set; } = new();

    [JsonPropertyName("outputs")]
    public List<string> Outputs { get; set; } = new();

    [JsonPropertyName("agent")]
    public string? Agent { get; set; }

    [JsonPropertyName("weight")]
    public double? Weight { get; set; }

    [JsonIgnore]
    public double EffectiveWeight => Math.Clamp(Weight ?? 1.0, 0.0, 1.0);
}

/// <summary>The on-disk book document: reserves and the flows between them.</summary>
public sealed class BookDocument
{
    [JsonPropertyName("reserves")]
    public List<ReserveRecord> Reserves { get; set; } = new();

    [JsonPropertyName("flows")]
    public List<FlowRecord> Flows { get; set; } = new();
}

/// <summary>Raised when a document cannot be assembled into a book.</summary>
public sealed class BookException : Exception
{
    public BookException(string message) : base(message) { }
}

/// <summary>Liquidity depth metrics.</summary>
public sealed record DepthReport(
    int TotalReserves,
    int FundedReserves,
    long WeightedDepth,
    IReadOnlyDictionary<string, long> BandBalances,
    IReadOnlyList<string> ThinIds,
    IReadOnlyList<string> DryIds,
    double DepthScore);
