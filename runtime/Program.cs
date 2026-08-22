using System.Text;
using System.Text.Json;

namespace VerityFlow.Runtime;

/// <summary>
/// VerityFlow.Runtime is a dependency-free companion to the Python core. It
/// ingests the JSON dossier emitted by <c>verityflow dossier --format json</c>
/// and produces a compact executive summary: verdict tallies, the weakest
/// claims that need more citations, and an overall provenance health grade.
/// </summary>
internal static class Program
{
    private static int Main(string[] args)
    {
        var options = CliOptions.Parse(args);
        if (options.ShowHelp)
        {
            PrintUsage();
            return 0;
        }

        string json;
        try
        {
            json = options.InputPath is null or "-"
                ? Console.In.ReadToEnd()
                : File.ReadAllText(options.InputPath);
        }
        catch (IOException ex)
        {
            Console.Error.WriteLine($"error: cannot read input: {ex.Message}");
            return 1;
        }

        Dossier dossier;
        try
        {
            dossier = DossierReader.Parse(json);
        }
        catch (JsonException ex)
        {
            Console.Error.WriteLine($"error: malformed dossier JSON: {ex.Message}");
            return 1;
        }

        var summary = Summariser.Summarise(dossier);
        string rendered = options.Format == OutputFormat.Json
            ? Summariser.RenderJson(summary)
            : Summariser.RenderText(summary);

        if (options.OutputPath is null or "-")
        {
            Console.Out.WriteLine(rendered);
        }
        else
        {
            File.WriteAllText(options.OutputPath, rendered);
        }

        // Non-zero exit if provenance health falls below the fail threshold.
        return summary.Grade == "F" ? 2 : 0;
    }

    private static void PrintUsage()
    {
        var sb = new StringBuilder();
        sb.AppendLine("VerityFlow.Runtime — dossier summariser");
        sb.AppendLine();
        sb.AppendLine("Usage:");
        sb.AppendLine("  VerityFlow.Runtime [--input <file>] [--output <file>] [--format text|json]");
        sb.AppendLine();
        sb.AppendLine("Reads a JSON dossier (from `verityflow dossier --format json`) and");
        sb.AppendLine("prints verdict tallies, weakest claims and a provenance health grade.");
        Console.Out.WriteLine(sb.ToString());
    }
}
