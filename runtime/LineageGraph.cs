namespace ArtifactLens.Runtime;

/// <summary>
/// The assembled, validated lineage graph and its traversal operations. This
/// is the C# counterpart to <c>artifactlens.graph</c> and produces identical
/// roots, leaves, ancestry and coverage as the Python implementation.
/// </summary>
public sealed class LineageGraph
{
    private readonly Dictionary<string, Artifact> _artifacts;
    private readonly Dictionary<string, Transformation> _transformations;
    private readonly Dictionary<string, List<string>> _producers;
    private readonly Dictionary<string, List<string>> _consumers;

    private LineageGraph(
        Dictionary<string, Artifact> artifacts,
        Dictionary<string, Transformation> transformations,
        Dictionary<string, List<string>> producers,
        Dictionary<string, List<string>> consumers)
    {
        _artifacts = artifacts;
        _transformations = transformations;
        _producers = producers;
        _consumers = consumers;
    }

    public IReadOnlyDictionary<string, Artifact> Artifacts => _artifacts;
    public IReadOnlyDictionary<string, Transformation> Transformations => _transformations;

    public IEnumerable<string> ArtifactIds => _artifacts.Keys.OrderBy(x => x, StringComparer.Ordinal);
    public IEnumerable<string> TransformationIds => _transformations.Keys.OrderBy(x => x, StringComparer.Ordinal);

    /// <summary>Build and validate a graph from a document.</summary>
