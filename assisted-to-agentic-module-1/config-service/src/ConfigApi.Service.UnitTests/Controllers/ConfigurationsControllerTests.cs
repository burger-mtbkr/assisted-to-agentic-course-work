using Microsoft.AspNetCore.Mvc;
using Moq;

namespace ConfigApi.Service.UnitTests.Controllers;

public class ConfigurationsControllerTests
{
    private readonly Mock<IConfigurationService> _configurationService = new();
    private readonly ConfigurationsController _controller;

    public ConfigurationsControllerTests()
    {
        _controller = new ConfigurationsController(_configurationService.Object);
    }

    [Fact]
    public void GetAll_ReturnsOkObjectResult()
    {
        _configurationService.Setup(s => s.GetAllForApplication("app-1")).Returns([]);

        var result = _controller.GetAll("app-1");

        Assert.IsType<OkObjectResult>(result);
    }

    [Fact]
    public void GetByKey_ReturnsOkObjectResult_WhenFound()
    {
        var configuration = new Configuration { ApplicationId = "app-1", ConfigKey = "key-a" };
        _configurationService.Setup(s => s.GetByKey("app-1", "key-a")).Returns(configuration);

        var result = _controller.GetByKey("app-1", "key-a");

        var okResult = Assert.IsType<OkObjectResult>(result);
        Assert.Same(configuration, okResult.Value);
    }

    [Fact]
    public void GetByKey_ReturnsNotFoundResult_WhenMissing()
    {
        _configurationService.Setup(s => s.GetByKey("app-1", "missing")).Returns((Configuration?)null);

        var result = _controller.GetByKey("app-1", "missing");

        Assert.IsType<NotFoundResult>(result);
    }

    [Fact]
    public async Task Create_ReturnsCreatedResult_WithLocation()
    {
        var created = new Configuration { ApplicationId = "app-1", ConfigKey = "key-a" };
        _configurationService
            .Setup(s => s.CreateAsync("app-1", It.IsAny<Configuration>()))
            .ReturnsAsync(created);

        var result = await _controller.Create("app-1", new Configuration { ConfigKey = "key-a", Value = "v" });

        var createdResult = Assert.IsType<CreatedAtActionResult>(result);
        Assert.Equal(nameof(ConfigurationsController.GetByKey), createdResult.ActionName);
        Assert.Same(created, createdResult.Value);
    }

    [Fact]
    public async Task Update_ReturnsOkObjectResult_WhenFound()
    {
        var updated = new Configuration { ApplicationId = "app-1", ConfigKey = "key-a", Value = "updated" };
        _configurationService
            .Setup(s => s.UpdateAsync("app-1", "key-a", It.IsAny<Configuration>()))
            .ReturnsAsync(updated);

        var result = await _controller.Update("app-1", "key-a", new Configuration { Value = "updated" });

        var okResult = Assert.IsType<OkObjectResult>(result);
        Assert.Same(updated, okResult.Value);
    }

    [Fact]
    public async Task Update_ReturnsNotFoundResult_WhenMissing()
    {
        _configurationService
            .Setup(s => s.UpdateAsync("app-1", "missing", It.IsAny<Configuration>()))
            .ReturnsAsync((Configuration?)null);

        var result = await _controller.Update("app-1", "missing", new Configuration { Value = "updated" });

        Assert.IsType<NotFoundResult>(result);
    }

    [Fact]
    public async Task Delete_ReturnsNoContentResult_WhenDeleted()
    {
        _configurationService.Setup(s => s.DeleteAsync("app-1", "key-a")).ReturnsAsync(true);

        var result = await _controller.Delete("app-1", "key-a");

        Assert.IsType<NoContentResult>(result);
    }

    [Fact]
    public async Task Delete_ReturnsNotFoundResult_WhenMissing()
    {
        _configurationService.Setup(s => s.DeleteAsync("app-1", "missing")).ReturnsAsync(false);

        var result = await _controller.Delete("app-1", "missing");

        Assert.IsType<NotFoundResult>(result);
    }
}
