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
