namespace CurveProtocol.Runtime;

/// <summary>
/// Liquidity depth scoring. Weighted, not raw: an edge tranche counts for less
/// than a core tranche because the edge is drained first.
/// </summary>
public static class Depth
{
    /// <summary>Micro-USDT per USDT.</summary>
    public const long Micro = 1_000_000;

    /// <summary>Tranches below this balance are reported as thin.</summary>
    public const long Floor = 250 * Micro;

    public static DepthReport Compute(Book book)
    {
        var bandBalances = Bands.All.ToDictionary(b => b, _ => 0L, StringComparer.Ordinal);
        var thin = new List<string>();
        var dry = new List<string>();

        long rawTotal = 0;
        long weighted = 0;
        var funded = 0;

        foreach (var id in book.ReserveIds())
        {
            var reserve = book.Reserves[id];
            var band = reserve.NormalisedBand;
            var weight = Math.Clamp(reserve.Weight ?? Bands.DefaultWeight(band), 0.0, 1.0);

            rawTotal += reserve.Balance;
            weighted += (long)Math.Round(reserve.Balance * (weight * Micro));
            bandBalances[band] = bandBalances[band] + reserve.Balance;

            if (reserve.Balance > 0)
            {
                funded++;
                if (reserve.Balance < Floor) thin.Add(id);
            }
            else if (!book.Flows.Values.Any(f => f.Outputs.Contains(id)))
            {
                dry.Add(id);
            }
        }

        var score = rawTotal > 0 ? (double)weighted / (rawTotal * (double)Micro) : 0.0;
        return new DepthReport(
            TotalReserves: book.Reserves.Count,
            FundedReserves: funded,
            WeightedDepth: weighted,
            BandBalances: bandBalances,
            ThinIds: thin.OrderBy(x => x, StringComparer.Ordinal).ToList(),
            DryIds: dry.OrderBy(x => x, StringComparer.Ordinal).ToList(),
            DepthScore: Math.Clamp(score, 0.0, 1.0));
    }

    public static string Grade(double score) => score switch
    {
        >= 0.85 => "A",
        >= 0.70 => "B",
        >= 0.55 => "C",
        >= 0.35 => "D",
        _ => "E",
    };

    /// <summary>Bands below <paramref name="target"/>, largest shortfall first.</summary>
    public static IEnumerable<(string Band, long Gap)> Shortfalls(DepthReport report, long target) =>
        report.BandBalances
            .Where(pair => pair.Value < target)
            .Select(pair => (Band: pair.Key, Gap: target - pair.Value))
            .OrderByDescending(row => row.Gap)
            .ThenBy(row => row.Band, StringComparer.Ordinal);
}
