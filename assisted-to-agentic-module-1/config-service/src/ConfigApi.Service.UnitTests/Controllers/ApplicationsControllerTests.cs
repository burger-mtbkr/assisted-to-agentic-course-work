using Microsoft.AspNetCore.Mvc;
using Moq;

namespace ConfigApi.Service.UnitTests.Controllers;

public class ApplicationsControllerTests
{
    private readonly Mock<IApplicationService> _applicationService = new();
    private readonly ApplicationsController _controller;

    public ApplicationsControllerTests()
    {
        _controller = new ApplicationsController(_applicationService.Object);
    }

    [Fact]
    public void GetAll_ReturnsOkObjectResult()
    {
        _applicationService.Setup(s => s.GetAll()).Returns([]);

        var result = _controller.GetAll();

        Assert.IsType<OkObjectResult>(result);
    }

    [Fact]
    public void GetById_ReturnsOkObjectResult_WhenFound()
    {
        var application = new Application { Id = "1", Name = "App" };
        _applicationService.Setup(s => s.GetById("1")).Returns(application);

        var result = _controller.GetById("1");

        var okResult = Assert.IsType<OkObjectResult>(result);
        Assert.Same(application, okResult.Value);
    }

    [Fact]
    public void GetById_ReturnsNotFoundResult_WhenMissing()
    {
        _applicationService.Setup(s => s.GetById("missing")).Returns((Application?)null);

        var result = _controller.GetById("missing");

        Assert.IsType<NotFoundResult>(result);
    }

    [Fact]
    public async Task Create_ReturnsCreatedResult_WithLocation()
    {
        var created = new Application { Id = "1", Name = "App" };
        _applicationService.Setup(s => s.CreateAsync(It.IsAny<Application>())).ReturnsAsync(created);

        var result = await _controller.Create(new Application { Name = "App" });

        var createdResult = Assert.IsType<CreatedAtActionResult>(result);
        Assert.Equal(nameof(ApplicationsController.GetById), createdResult.ActionName);
        Assert.Same(created, createdResult.Value);
    }

    [Fact]
    public async Task Update_ReturnsOkObjectResult_WhenFound()
    {
        var updated = new Application { Id = "1", Name = "Updated" };
        _applicationService.Setup(s => s.UpdateAsync("1", It.IsAny<Application>())).ReturnsAsync(updated);

        var result = await _controller.Update("1", new Application { Name = "Updated" });

        var okResult = Assert.IsType<OkObjectResult>(result);
        Assert.Same(updated, okResult.Value);
    }

    [Fact]
    public async Task Update_ReturnsNotFoundResult_WhenMissing()
    {
        _applicationService.Setup(s => s.UpdateAsync("missing", It.IsAny<Application>())).ReturnsAsync((Application?)null);

        var result = await _controller.Update("missing", new Application { Name = "Updated" });

        Assert.IsType<NotFoundResult>(result);
    }

    [Fact]
    public async Task Delete_ReturnsNoContentResult_WhenDeleted()
    {
        _applicationService.Setup(s => s.DeleteAsync("1")).ReturnsAsync(true);

        var result = await _controller.Delete("1");

        Assert.IsType<NoContentResult>(result);
    }

    [Fact]
    public async Task Delete_ReturnsNotFoundResult_WhenMissing()
    {
        _applicationService.Setup(s => s.DeleteAsync("missing")).ReturnsAsync((bool?)null);

        var result = await _controller.Delete("missing");

        Assert.IsType<NotFoundResult>(result);
    }

    [Fact]
    public async Task Delete_ReturnsConflictResult_WhenConfigurationsExist()
    {
        _applicationService.Setup(s => s.DeleteAsync("1")).ReturnsAsync(false);

        var result = await _controller.Delete("1");

        Assert.IsType<ConflictResult>(result);
    }
}
