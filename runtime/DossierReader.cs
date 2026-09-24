using System.Text.Json;

namespace VerityFlow.Runtime;

internal sealed record ClaimEntry(
    string ClaimId,
    string ClaimText,
    string Topic,
    string Verdict,
    double SupportIndex,
    double Diversity,
    int QuotationCount);

internal sealed record Dossier(
    string Title,
    double Coverage,
    double MeanSupport,
    double MeanDiversity,
    int Claims,
    int Sources,
    int Quotations,
    int Links,
    IReadOnlyList<ClaimEntry> Entries);

/// <summary>Parses the Python-emitted dossier JSON using only System.Text.Json.</summary>
internal static class DossierReader
{
    public static Dossier Parse(string json)
    {
        using var doc = JsonDocument.Parse(json);
        JsonElement root = doc.RootElement;

        string title = GetString(root, "title", "Evidence Dossier");

        double coverage = 0, meanSupport = 0, meanDiversity = 0;
        if (root.TryGetProperty("summary", out var summary))
        {
            coverage = GetDouble(summary, "coverage");
            meanSupport = GetDouble(summary, "mean_support");
            meanDiversity = GetDouble(summary, "mean_diversity");
        }

        int claims = 0, sources = 0, quotations = 0, links = 0;
        if (root.TryGetProperty("graph_stats", out var stats))
        {
            claims = GetInt(stats, "claims");
            sources = GetInt(stats, "sources");
            quotations = GetInt(stats, "quotations");
            links = GetInt(stats, "links");
        }

        var entries = new List<ClaimEntry>();
        if (root.TryGetProperty("entries", out var arr) && arr.ValueKind == JsonValueKind.Array)
        {
            foreach (JsonElement e in arr.EnumerateArray())
            {
                int quoteCount = 0;
                if (e.TryGetProperty("quotations", out var quotes) &&
                    quotes.ValueKind == JsonValueKind.Array)
                {
                    quoteCount = quotes.GetArrayLength();
                }

                entries.Add(new ClaimEntry(
                    GetString(e, "claim_id", ""),
                    GetString(e, "claim_text", ""),
                    GetString(e, "topic", "general"),
                    GetString(e, "verdict", "unsupported"),
                    GetDouble(e, "support_index"),
                    GetDouble(e, "diversity"),
                    quoteCount));
            }
        }

        return new Dossier(title, coverage, meanSupport, meanDiversity,
            claims, sources, quotations, links, entries);
    }

    private static string GetString(JsonElement el, string name, string fallback) =>
        el.TryGetProperty(name, out var v) && v.ValueKind == JsonValueKind.String
            ? v.GetString() ?? fallback
            : fallback;

    private static double GetDouble(JsonElement el, string name) =>
        el.TryGetProperty(name, out var v) && v.ValueKind == JsonValueKind.Number
            ? v.GetDouble()
            : 0.0;

    private static int GetInt(JsonElement el, string name) =>
        el.TryGetProperty(name, out var v) && v.ValueKind == JsonValueKind.Number
            ? v.GetInt32()
            : 0;
}
