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
