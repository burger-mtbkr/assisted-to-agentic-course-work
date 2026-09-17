namespace ConfigApi.Service.Models.Configurations;

public record Configuration
{
    public string ApplicationId { get; set; } = string.Empty;

    public string ConfigKey { get; set; } = string.Empty;

    public string Value { get; set; } = string.Empty;

    public string? Description { get; set; }

    public DateTime CreatedDate { get; set; }
}
