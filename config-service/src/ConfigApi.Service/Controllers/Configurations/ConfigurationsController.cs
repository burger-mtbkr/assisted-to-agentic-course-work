using Microsoft.AspNetCore.Mvc;

namespace ConfigApi.Service.Controllers.Configurations;

[ApiController]
[Route("api/v1/applications/{applicationId}/configurations")]
public class ConfigurationsController : ControllerBase
{
    private readonly IConfigurationService _configurationService;

    public ConfigurationsController(IConfigurationService configurationService)
    {
        _configurationService = configurationService;
    }

    [HttpGet]
    [ProducesResponseType(typeof(IReadOnlyList<Configuration>), StatusCodes.Status200OK)]
    public IActionResult GetAll(string applicationId)
    {
        return Ok(_configurationService.GetAllForApplication(applicationId));
    }

    [HttpGet("{configKey}")]
    [ProducesResponseType(typeof(Configuration), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public IActionResult GetByKey(string applicationId, string configKey)
    {
        var configuration = _configurationService.GetByKey(applicationId, configKey);
        return configuration is null ? NotFound() : Ok(configuration);
    }

    [HttpPost]
    [ProducesResponseType(typeof(Configuration), StatusCodes.Status201Created)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status409Conflict)]
    public async Task<IActionResult> Create(string applicationId, [FromBody] Configuration configuration)
    {
        var created = await _configurationService.CreateAsync(applicationId, configuration);
        return CreatedAtAction(nameof(GetByKey), new { applicationId, configKey = created.ConfigKey }, created);
    }

    [HttpPut("{configKey}")]
    [ProducesResponseType(typeof(Configuration), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> Update(string applicationId, string configKey, [FromBody] Configuration configuration)
    {
        var updated = await _configurationService.UpdateAsync(applicationId, configKey, configuration);
        return updated is null ? NotFound() : Ok(updated);
    }

    [HttpDelete("{configKey}")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> Delete(string applicationId, string configKey)
    {
        var deleted = await _configurationService.DeleteAsync(applicationId, configKey);
        return deleted ? NoContent() : NotFound();
    }
}
