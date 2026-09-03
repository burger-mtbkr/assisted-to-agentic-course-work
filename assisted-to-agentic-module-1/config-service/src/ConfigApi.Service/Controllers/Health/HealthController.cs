using Microsoft.AspNetCore.Mvc;

namespace ConfigApi.Service.Controllers.Health;

[ApiController]
[Route("health")]
public class HealthController : ControllerBase
{
    [HttpGet]
    [ProducesResponseType(StatusCodes.Status200OK)]
    public IActionResult Get()
    {
        return Ok(new { status = "healthy" });
    }
}
