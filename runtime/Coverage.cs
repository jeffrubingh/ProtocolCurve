using System.Security.Cryptography;
using System.Text;

namespace ArtifactLens.Runtime;

/// <summary>
/// Provenance coverage scoring and graph digest. The weights and algorithm
/// match <c>artifactlens.coverage</c> exactly so the runtime and the Python
/// package report the same score for the same graph.
/// </summary>
public static class Coverage
{
    public const double WConnectivity = 0.30;
    public const double WVerification = 0.25;
    public const double WRootedness = 0.30;
    public const double WConfidence = 0.15;

    private const double WeightSum = WConnectivity + WVerification + WRootedness + WConfidence;

    public static CoverageReport Compute(LineageGraph graph)
    {
        int total = graph.Artifacts.Count;
        if (total == 0)
            return new CoverageReport();

        var roots = new HashSet<string>(graph.Roots(), StringComparer.Ordinal);
        int connected = 0, verified = 0, rooted = 0;
        var orphans = new List<string>();
        var dangling = new List<string>();

        foreach (var aid in graph.ArtifactIds)
        {
            bool hasProducer = graph.Parents(aid).Count > 0 ||
                               graph.Transformations.Values.Any(t => t.Outputs.Contains(aid));
            bool hasConsumer = graph.Transformations.Values.Any(t => t.Inputs.Contains(aid));

            if (hasProducer || hasConsumer) connected++;
            else orphans.Add(aid);

            if (graph.Artifacts[aid].IsVerified) verified++;
            if (graph.ReachesRoot(aid, roots)) rooted++;
            if (!roots.Contains(aid) && !hasProducer) dangling.Add(aid);
        }

        double meanConf = MeanConfidence(graph);
        double connectivity = (double)connected / total;
        double verification = (double)verified / total;
        double rootedness = (double)rooted / total;

        double score = (WConnectivity * connectivity
                        + WVerification * verification
                        + WRootedness * rootedness
                        + WConfidence * meanConf) / WeightSum;

        orphans.Sort(StringComparer.Ordinal);
        dangling.Sort(StringComparer.Ordinal);

        return new CoverageReport
        {
            TotalArtifacts = total,
            ConnectedArtifacts = connected,
            VerifiedArtifacts = verified,
            RootedArtifacts = rooted,
            OrphanIds = orphans,
            DanglingIds = dangling,
            CoverageScore = score,
        };
    }

    private static double MeanConfidence(LineageGraph graph)
    {
        if (graph.Transformations.Count == 0) return 1.0;
        double total = graph.Transformations.Values.Sum(t => t.EffectiveConfidence);
        return total / graph.Transformations.Count;
    }

    public static string Grade(double score) => score switch
    {
        >= 0.90 => "A",
        >= 0.75 => "B",
        >= 0.60 => "C",
        >= 0.40 => "D",
        _ => "F",
    };

    /// <summary>Stable SHA-256 digest matching the Python <c>digest_graph</c>.</summary>
    public static string DigestGraph(LineageGraph graph)
    {
        var sb = new StringBuilder();
        foreach (var aid in graph.ArtifactIds)
        {
            var art = graph.Artifacts[aid];
            sb.Append($"A|{art.Id}|{art.Kind}|{art.ContentHash ?? ""}\n");
        }
        foreach (var tid in graph.TransformationIds)
        {
            var tr = graph.Transformations[tid];
            var ins = string.Join(",", tr.Inputs.OrderBy(x => x, StringComparer.Ordinal));
            var outs = string.Join(",", tr.Outputs.OrderBy(x => x, StringComparer.Ordinal));
            sb.Append($"T|{tr.Id}|{tr.Op}|{ins}|{outs}\n");
        }
        var bytes = SHA256.HashData(Encoding.UTF8.GetBytes(sb.ToString()));
        return Convert.ToHexStringLower(bytes);
    }
}
