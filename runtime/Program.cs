using System.Globalization;
using System.Text;
using System.Text.Json;

namespace CurveProtocol.Runtime;

/// <summary>
/// The native runtime. Reads a book document and prints origins, depth, the
/// stable digest or the projected curve. It is the fast companion to the Python
/// package and shares the same on-disk format and the same fingerprint.
/// </summary>
public static class Program
{
    public static int Main(string[] args)
    {
        if (args.Length == 0 || args[0] is "-h" or "--help")
        {
            PrintHelp();
            return args.Length == 0 ? 2 : 0;
        }

        var command = args[0];

        if (command == "curve")
        {
            return RunCurve(args.Skip(1).ToArray());
        }

        var path = args.Length > 1 ? args[1] : "";
        if (string.IsNullOrEmpty(path))
        {
            Console.Error.WriteLine("error: missing book document path");
            return 2;
        }

        try
        {
            var options = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };
            var document = JsonSerializer.Deserialize<BookDocument>(File.ReadAllText(path), options)
                           ?? throw new BookException("empty or invalid book document");
            var book = Book.Build(document);

            return command switch
            {
                "origins" => RunOrigins(book),
                "depth" => RunDepth(book),
                "digest" => RunDigest(book),
                "trajectory" => RunTrajectory(book),
                _ => Unknown(command),
            };
        }
        catch (BookException ex)
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

    private static int RunOrigins(Book book)
    {
        Console.WriteLine("ORIGINS");
        foreach (var id in book.Origins())
        {
            var r = book.Reserves[id];
            Console.WriteLine($"  {id}  [{r.NormalisedBand}]  {r.DisplayLabel}");
        }
        Console.WriteLine("TERMINALS");
        foreach (var id in book.Terminals())
        {
            var r = book.Reserves[id];
            Console.WriteLine($"  {id}  [{r.NormalisedBand}]  {r.DisplayLabel}");
        }
        return 0;
    }

    private static int RunDepth(Book book)
    {
        var report = Depth.Compute(book);
        Console.WriteLine($"depth score    : {report.DepthScore:F4} (grade {Depth.Grade(report.DepthScore)})");
        Console.WriteLine($"weighted       : {report.WeightedDepth / (double)Depth.Micro:F6} USDT");
        Console.WriteLine($"funded         : {report.FundedReserves}/{report.TotalReserves}");
        foreach (var band in report.BandBalances.Keys.OrderBy(k => k, StringComparer.Ordinal))
            Console.WriteLine($"  {band,-8} {report.BandBalances[band] / (double)Depth.Micro:F6}");
        foreach (var (band, gap) in Depth.Shortfalls(report, 1000 * Depth.Micro))
            Console.WriteLine($"short {band,-8} {gap / (double)Depth.Micro:F6} USDT below target");
        if (report.ThinIds.Count > 0)
            Console.WriteLine($"thin           : {string.Join(", ", report.ThinIds)}");
        if (report.DryIds.Count > 0)
            Console.WriteLine($"dry            : {string.Join(", ", report.DryIds)}");
        return 0;
    }

    private static int RunDigest(Book book)
    {
        Console.WriteLine(book.Digest());
        return 0;
    }

    private static int RunTrajectory(Book book)
    {
        var report = Depth.Compute(book);
        Console.WriteLine("TRAJECTORY");
        Console.WriteLine($"book digest     : {book.Digest()}");
        Console.WriteLine();
        Console.WriteLine($"origins         : {string.Join(", ", book.Origins())}");
        Console.WriteLine($"terminals       : {string.Join(", ", book.Terminals())}");
        Console.WriteLine();
        Console.WriteLine($"depth            : {report.DepthScore:F4}");
        Console.WriteLine($"weighted         : {report.WeightedDepth / (double)Depth.Micro:F6} USDT");
        Console.WriteLine($"funded           : {report.FundedReserves}/{report.TotalReserves}");
        Console.WriteLine();
        Console.WriteLine("PATHS");
        foreach (var terminal in book.Terminals())
        {
            var chain = book.Ancestry(terminal).Append(terminal);
            Console.WriteLine($"  {terminal}: {string.Join(" -> ", chain)}");
        }
        return 0;
    }

    private static int RunCurve(string[] args)
    {
        if (args.Length == 0 || !long.TryParse(args[0], out var seed))
        {
            Console.Error.WriteLine("usage: curve <seed_usdt> [rate_bps] [ceiling_usdt] [epochs]");
            return 2;
        }
        var rate = args.Length > 1 ? int.Parse(args[1], CultureInfo.InvariantCulture) : 250;
        var ceiling = args.Length > 2 ? long.Parse(args[2], CultureInfo.InvariantCulture) : 0;
        var epochs = args.Length > 3 ? int.Parse(args[3], CultureInfo.InvariantCulture) : 12;

        var value = seed * Depth.Micro;
        var cap = ceiling * Depth.Micro;
        Console.WriteLine($"{0,4}  {value / (double)Depth.Micro:F6}");
        for (var epoch = 1; epoch <= epochs; epoch++)
        {
            value = Compound(value, rate, cap);
            Console.WriteLine($"{epoch,4}  {value / (double)Depth.Micro:F6}");
        }
        return 0;
    }

    private static long Compound(long balance, int rateBps, long ceiling)
    {
        if (balance <= 0) return 0;
        var grown = balance + (balance * Math.Max(0, rateBps)) / 10_000;
        return ceiling > 0 ? Math.Min(grown, ceiling) : grown;
    }

    private static int Unknown(string command)
    {
        Console.Error.WriteLine($"error: unknown command: {command}");
        return 2;
    }

    private static void PrintHelp()
    {
        Console.WriteLine("CurveProtocol.Runtime — native book engine");
        Console.WriteLine();
        Console.WriteLine("usage: CurveProtocol.Runtime <command> <book.json>");
        Console.WriteLine();
        Console.WriteLine("commands:");
        Console.WriteLine("  origins     list origin and terminal tranches");
        Console.WriteLine("  depth       print the liquidity depth report");
        Console.WriteLine("  digest      print the stable book digest");
        Console.WriteLine("  trajectory  print a compact trajectory report");
        Console.WriteLine("  curve       project the growth curve (no document needed)");
    }
}
