using ConfigApi.Service.Services.Applications;
using ConfigApi.Service.Services.Configurations;

namespace ConfigApi.Service.Ignition;

public static class ServicesIgnition
{
    public static void ConfigureServices(this IServiceCollection services)
    {
        services.AddScoped<IApplicationService, ApplicationService>();
        services.AddScoped<IConfigurationService, ConfigurationService>();
    }
}
