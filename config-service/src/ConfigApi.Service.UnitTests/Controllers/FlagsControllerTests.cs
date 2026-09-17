using Microsoft.AspNetCore.Mvc;
using Moq;

namespace ConfigApi.Service.UnitTests.Controllers;

public class FlagsControllerTests
{
    private readonly Mock<IFlagService> _flagService = new();
    private readonly FlagsController _controller;

    public FlagsControllerTests()
    {
        _controller = new FlagsController(_flagService.Object);
    }

    [Fact]
    public void GetAll_ReturnsOkObjectResult()
    {
        _flagService.Setup(s => s.GetAllForApplication("app-1")).Returns([]);

        var result = _controller.GetAll("app-1");

        Assert.IsType<OkObjectResult>(result);
    }

    [Fact]
    public void GetByKey_ReturnsOkObjectResult_WhenFound()
    {
        var flag = new Flag { ApplicationId = "app-1", FlagKey = "flag-a" };
        _flagService.Setup(s => s.GetByKey("app-1", "flag-a")).Returns(flag);

        var result = _controller.GetByKey("app-1", "flag-a");

        var okResult = Assert.IsType<OkObjectResult>(result);
        Assert.Same(flag, okResult.Value);
    }

    [Fact]
    public void GetByKey_ReturnsNotFoundResult_WhenMissing()
    {
        _flagService.Setup(s => s.GetByKey("app-1", "missing")).Returns((Flag?)null);

        var result = _controller.GetByKey("app-1", "missing");

        Assert.IsType<NotFoundResult>(result);
    }

    [Fact]
    public async Task Create_ReturnsCreatedResult_WithLocation()
    {
        var created = new Flag { ApplicationId = "app-1", FlagKey = "flag-a" };
        _flagService
            .Setup(s => s.CreateAsync("app-1", It.IsAny<Flag>()))
            .ReturnsAsync(created);

        var result = await _controller.Create("app-1", new Flag { FlagKey = "flag-a", Enabled = true });

        var createdResult = Assert.IsType<CreatedAtActionResult>(result);
        Assert.Equal(nameof(FlagsController.GetByKey), createdResult.ActionName);
        Assert.Same(created, createdResult.Value);
    }

    [Fact]
    public async Task Update_ReturnsOkObjectResult_WhenFound()
    {
        var updated = new Flag { ApplicationId = "app-1", FlagKey = "flag-a", Enabled = true };
        _flagService
            .Setup(s => s.UpdateAsync("app-1", "flag-a", It.IsAny<Flag>()))
            .ReturnsAsync(updated);

        var result = await _controller.Update("app-1", "flag-a", new Flag { Enabled = true });

        var okResult = Assert.IsType<OkObjectResult>(result);
        Assert.Same(updated, okResult.Value);
    }

    [Fact]
    public async Task Update_ReturnsNotFoundResult_WhenMissing()
    {
        _flagService
            .Setup(s => s.UpdateAsync("app-1", "missing", It.IsAny<Flag>()))
            .ReturnsAsync((Flag?)null);

        var result = await _controller.Update("app-1", "missing", new Flag { Enabled = true });

        Assert.IsType<NotFoundResult>(result);
    }

    [Fact]
    public async Task Delete_ReturnsNoContentResult_WhenDeleted()
    {
        _flagService.Setup(s => s.DeleteAsync("app-1", "flag-a")).ReturnsAsync(true);

        var result = await _controller.Delete("app-1", "flag-a");

        Assert.IsType<NoContentResult>(result);
    }

    [Fact]
    public async Task Delete_ReturnsNotFoundResult_WhenMissing()
    {
        _flagService.Setup(s => s.DeleteAsync("app-1", "missing")).ReturnsAsync(false);

        var result = await _controller.Delete("app-1", "missing");

        Assert.IsType<NotFoundResult>(result);
    }
}
