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
