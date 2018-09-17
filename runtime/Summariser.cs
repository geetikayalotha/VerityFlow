using System.Globalization;
using System.Text;
using System.Text.Json;

namespace VerityFlow.Runtime;

internal sealed record Summary(
    string Title,
    string Grade,
    double HealthScore,
    double Coverage,
    double MeanSupport,
    double MeanDiversity,
    int TotalClaims,
    IReadOnlyDictionary<string, int> VerdictTally,
    IReadOnlyList<ClaimEntry> WeakestClaims);

/// <summary>
/// Turns a parsed <see cref="Dossier"/> into an executive <see cref="Summary"/>.
///
/// The provenance <b>health score</b> blends three normalised signals:
/// coverage (40%), mean support (35%) and mean diversity (25%). It is graded
/// on a fixed scale so a reviewer can triage a report at a glance.
/// </summary>
internal static class Summariser
{
    private const int WeakestLimit = 5;

    public static Summary Summarise(Dossier dossier)
    {
        var tally = new SortedDictionary<string, int>(StringComparer.Ordinal);
        foreach (ClaimEntry e in dossier.Entries)
        {
            tally[e.Verdict] = tally.TryGetValue(e.Verdict, out int n) ? n + 1 : 1;
        }

        double health =
            (dossier.Coverage * 0.40) +
            (dossier.MeanSupport * 0.35) +
            (dossier.MeanDiversity * 0.25);
        health = Math.Round(Math.Clamp(health, 0.0, 1.0), 4);

        var weakest = dossier.Entries
            .OrderBy(e => e.SupportIndex)
            .ThenBy(e => e.Diversity)
            .Take(WeakestLimit)
            .ToList();

        return new Summary(
            dossier.Title,
            Grade(health),
            health,
            dossier.Coverage,
            dossier.MeanSupport,
