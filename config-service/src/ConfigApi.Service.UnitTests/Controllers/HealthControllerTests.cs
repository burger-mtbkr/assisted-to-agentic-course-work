using Microsoft.AspNetCore.Mvc;

namespace ConfigApi.Service.UnitTests.Controllers;

public class HealthControllerTests
{
    [Fact]
    public void Get_ReturnsOkObjectResult()
    {
        var controller = new HealthController();

        var result = controller.Get();

        var okResult = Assert.IsType<OkObjectResult>(result);
        Assert.NotNull(okResult.Value);
    }
}
