using System.Text.Json;

namespace ArtifactLens.Runtime;

/// <summary>
/// The ArtifactLens native runtime. It parses a graph document, builds the
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
            Console.Error.WriteLine("usage: ArtifactLens.Runtime <command> [graph.json]");
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
