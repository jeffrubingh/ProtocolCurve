using System.Text.Json;

namespace CurveProtocol.Runtime;

/// <summary>
/// The CurveProtocol native runtime. It parses a graph document, builds the
/// lineage graph, and prints roots, coverage and the stable digest. It is used
/// as a fast verification companion to the Python package and shares the same
/// on-disk graph document format.
/// </summary>
public static class Program
{
    public static int Main(string[] args)
    {
        if (args.Length == 0)
        {
            Console.Error.WriteLine("usage: CurveProtocol.Runtime <command> [graph.json]");
            Console.Error.WriteLine("commands: roots | coverage | digest | dossier");
            return 2;
        }

        string command = args[0];
        string path = args.Length > 1 ? args[1] : "";

        if (command == "--help" || command == "-h")
        {
            PrintHelp();
            return 0;
        }

        if (string.IsNullOrEmpty(path))
        {
            Console.Error.WriteLine("error: missing graph document path");
            return 2;
        }

        try
        {
            var options = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };
            var text = File.ReadAllText(path);
            var doc = JsonSerializer.Deserialize<GraphDocument>(text, options)
                      ?? throw new GraphException("empty or invalid graph document");
            var graph = LineageGraph.Build(doc);

            return command switch
            {
                "roots" => RunRoots(graph),
                "coverage" => RunCoverage(graph),
                "digest" => RunDigest(graph),
                "dossier" => RunDossier(graph),
                _ => Unknown(command),
            };
        }
        catch (GraphException ex)
        {
            Console.Error.WriteLine($"error: {ex.Message}");
            return 1;
        }
        catch (FileNotFoundException)
        {
            Console.Error.WriteLine($"error: file not found: {path}");
            return 1;
        }
    }

    private static int RunRoots(LineageGraph graph)
    {
        Console.WriteLine("ROOTS");
        foreach (var id in graph.Roots())
        {
            var a = graph.Artifacts[id];
            Console.WriteLine($"  {id}  [{a.Kind}]  {a.Label}");
        }
        Console.WriteLine("LEAVES");
        foreach (var id in graph.Leaves())
        {
            var a = graph.Artifacts[id];
            Console.WriteLine($"  {id}  [{a.Kind}]  {a.Label}");
        }
        return 0;
    }

    private static int RunCoverage(LineageGraph graph)
    {
        var cov = Coverage.Compute(graph);
        Console.WriteLine($"coverage score : {cov.CoverageScore:F4} (grade {Coverage.Grade(cov.CoverageScore)})");
        Console.WriteLine($"connected      : {cov.ConnectedArtifacts}/{cov.TotalArtifacts}");
        Console.WriteLine($"verified       : {cov.VerifiedArtifacts}/{cov.TotalArtifacts}");
        Console.WriteLine($"rooted         : {cov.RootedArtifacts}/{cov.TotalArtifacts}");
        if (cov.OrphanIds.Count > 0)
            Console.WriteLine($"orphans        : {string.Join(", ", cov.OrphanIds)}");
        if (cov.DanglingIds.Count > 0)
            Console.WriteLine($"dangling       : {string.Join(", ", cov.DanglingIds)}");
        return 0;
    }

    private static int RunDigest(LineageGraph graph)
    {
        Console.WriteLine(Coverage.DigestGraph(graph));
        return 0;
    }

    private static int RunDossier(LineageGraph graph)
    {
        var cov = Coverage.Compute(graph);
        Console.WriteLine("========================================================================");
        Console.WriteLine("ARTIFACTLENS PROVENANCE DOSSIER (runtime)");
        Console.WriteLine("========================================================================");
        Console.WriteLine($"graph digest : {Coverage.DigestGraph(graph)}");
        Console.WriteLine($"artifacts    : {cov.TotalArtifacts}");
        Console.WriteLine($"roots        : {graph.Roots().Count}");
        Console.WriteLine($"leaves       : {graph.Leaves().Count}");
        Console.WriteLine($"score        : {cov.CoverageScore:F4} (grade {Coverage.Grade(cov.CoverageScore)})");
        Console.WriteLine("LEAVES & LINEAGE");
        foreach (var leaf in graph.Leaves())
        {
            var chain = graph.Ancestry(leaf).Append(leaf);
            Console.WriteLine($"  {leaf}: {string.Join(" -> ", chain)}");
        }
        return 0;
    }

    private static int Unknown(string command)
    {
        Console.Error.WriteLine($"error: unknown command: {command}");
        return 2;
    }

    private static void PrintHelp()
    {
        Console.WriteLine("CurveProtocol.Runtime — native provenance engine");
        Console.WriteLine();
        Console.WriteLine("usage: CurveProtocol.Runtime <command> <graph.json>");
        Console.WriteLine();
        Console.WriteLine("commands:");
        Console.WriteLine("  roots     list root and leaf artifacts");
        Console.WriteLine("  coverage  print provenance coverage report");
        Console.WriteLine("  digest    print the stable graph digest");
        Console.WriteLine("  dossier   print a compact dossier report");
    }
}
