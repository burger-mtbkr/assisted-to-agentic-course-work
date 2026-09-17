namespace ConfigApi.Service.Models.Common;

public record BaseModel
{
    public string Id { get; set; } = string.Empty;

    public DateTime CreatedDate { get; set; }
}
