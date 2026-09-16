namespace ConfigApi.Service.Ignition;

public static class CorsIgnition
{
    public const string LocalDevPolicy = "LocalDev";

    public static void ConfigureCors(this WebApplicationBuilder builder)
    {
        builder.Services.AddCors(options =>
        {
            options.AddPolicy(LocalDevPolicy, policy =>
            {
                policy
                    .WithOrigins("http://localhost:5173", "http://127.0.0.1:5173")
                    .AllowAnyMethod()
                    .AllowAnyHeader();
            });
        });
    }
}
