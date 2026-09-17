namespace ConfigApi.Service.Models.Applications;

public record Application : BaseModel
{
    public string Name { get; set; } = string.Empty;

    public string? Description { get; set; }
}
