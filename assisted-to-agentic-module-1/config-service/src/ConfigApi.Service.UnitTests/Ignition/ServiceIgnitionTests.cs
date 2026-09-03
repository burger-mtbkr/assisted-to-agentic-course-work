using ConfigApi.Service.Ignition;
using Microsoft.Extensions.DependencyInjection;

namespace ConfigApi.Service.UnitTests.Ignition;

public class ServiceIgnitionTests
{
    [Fact]
    public void ConfigureServices_RegistersApplicationService_AsScoped()
    {
        var services = new ServiceCollection();

        services.ConfigureServices();

        var descriptor = Assert.Single(services, d => d.ServiceType == typeof(IApplicationService));
        Assert.Equal(typeof(ApplicationService), descriptor.ImplementationType);
        Assert.Equal(ServiceLifetime.Scoped, descriptor.Lifetime);
    }

    [Fact]
    public void ConfigureServices_RegistersConfigurationService_AsScoped()
    {
        var services = new ServiceCollection();

        services.ConfigureServices();

        var descriptor = Assert.Single(services, d => d.ServiceType == typeof(IConfigurationService));
        Assert.Equal(typeof(ConfigurationService), descriptor.ImplementationType);
        Assert.Equal(ServiceLifetime.Scoped, descriptor.Lifetime);
    }
}
