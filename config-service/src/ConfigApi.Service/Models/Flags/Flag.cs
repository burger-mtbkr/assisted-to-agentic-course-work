namespace ConfigApi.Service.Models.Flags;

public record Flag
{
    public string ApplicationId { get; set; } = string.Empty;

    public string FlagKey { get; set; } = string.Empty;

    public bool Enabled { get; set; }

    public string? Description { get; set; }

    public DateTime CreatedDate { get; set; }
}
