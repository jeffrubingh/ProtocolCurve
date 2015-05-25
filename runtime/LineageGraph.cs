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
    /// <exception cref="GraphException">On duplicate ids, cycles, or (strict) missing endpoints.</exception>
    public static LineageGraph Build(GraphDocument doc, bool strict = true)
    {
        var artifacts = new Dictionary<string, Artifact>(StringComparer.Ordinal);
        foreach (var art in doc.Artifacts)
        {
            var norm = art with { Label = string.IsNullOrEmpty(art.Label) ? art.Id : art.Label };
            if (!artifacts.TryAdd(norm.Id, norm))
                throw new GraphException($"duplicate artifact id: {norm.Id}");
        }

        var transformations = new Dictionary<string, Transformation>(StringComparer.Ordinal);
        foreach (var tr in doc.Transformations)
        {
            if (!transformations.TryAdd(tr.Id, tr))
                throw new GraphException($"duplicate transformation id: {tr.Id}");
        }

        foreach (var tr in transformations.Values)
        {
            foreach (var endpoint in tr.Inputs.Concat(tr.Outputs))
            {
                if (!artifacts.ContainsKey(endpoint))
                {
                    if (strict)
                        throw new GraphException(
                            $"transformation {tr.Id} references unknown artifact {endpoint}");
                    artifacts[endpoint] = new Artifact { Id = endpoint, Label = endpoint };
                }
            }
        }

        var producers = artifacts.Keys.ToDictionary(k => k, _ => new List<string>(), StringComparer.Ordinal);
        var consumers = artifacts.Keys.ToDictionary(k => k, _ => new List<string>(), StringComparer.Ordinal);
        foreach (var tid in transformations.Keys.OrderBy(x => x, StringComparer.Ordinal))
        {
            var tr = transformations[tid];
            foreach (var outId in tr.Outputs) producers[outId].Add(tid);
            foreach (var inId in tr.Inputs) consumers[inId].Add(tid);
        }

        var graph = new LineageGraph(artifacts, transformations, producers, consumers);
        graph.AssertAcyclic();
        return graph;
    }

    public IReadOnlyList<string> Parents(string artifactId)
    {
        var seen = new List<string>();
        foreach (var tid in _producers.GetValueOrDefault(artifactId, new List<string>()))
            foreach (var src in _transformations[tid].Inputs)
                if (!seen.Contains(src)) seen.Add(src);
        seen.Sort(StringComparer.Ordinal);
        return seen;
    }

    public IReadOnlyList<string> Children(string artifactId)
    {
        var seen = new List<string>();
        foreach (var tid in _consumers.GetValueOrDefault(artifactId, new List<string>()))
            foreach (var dst in _transformations[tid].Outputs)
                if (!seen.Contains(dst)) seen.Add(dst);
        seen.Sort(StringComparer.Ordinal);
        return seen;
    }

