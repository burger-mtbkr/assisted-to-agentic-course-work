using Serilog;
using Serilog.Events;

namespace ConfigApi.Service.Ignition;

public static class LogIgnition
{
    public static void ConfigureLogging(this WebApplicationBuilder builder)
    {
        builder.Host.UseSerilog((context, services, configuration) =>
        {
            configuration
                .Enrich.FromLogContext()
                .MinimumLevel.Information()
                .MinimumLevel.Override("Microsoft", LogEventLevel.Warning)
                .WriteTo.Console();
        });
    }
}
