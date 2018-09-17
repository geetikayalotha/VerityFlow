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
