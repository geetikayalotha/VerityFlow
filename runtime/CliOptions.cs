namespace VerityFlow.Runtime;

internal enum OutputFormat
{
    Text,
    Json,
}

/// <summary>Minimal, allocation-light argument parser for the summariser.</summary>
internal sealed class CliOptions
{
    public string? InputPath { get; private set; }
    public string? OutputPath { get; private set; }
    public OutputFormat Format { get; private set; } = OutputFormat.Text;
    public bool ShowHelp { get; private set; }

    public static CliOptions Parse(string[] args)
    {
        var opts = new CliOptions();
        for (int i = 0; i < args.Length; i++)
        {
            switch (args[i])
            {
                case "-h":
                case "--help":
                    opts.ShowHelp = true;
                    break;
                case "-i":
                case "--input":
                    opts.InputPath = NextValue(args, ref i);
                    break;
