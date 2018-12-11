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
