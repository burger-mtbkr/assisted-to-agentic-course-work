using Microsoft.AspNetCore.Mvc;

namespace ConfigApi.Service.Controllers.Flags;

[ApiController]
[Route("api/v1/applications/{applicationId}/flags")]
public class FlagsController : ControllerBase
{
    private readonly IFlagService _flagService;

    public FlagsController(IFlagService flagService)
    {
        _flagService = flagService;
    }

    [HttpGet]
    [ProducesResponseType(typeof(IReadOnlyList<Flag>), StatusCodes.Status200OK)]
    public IActionResult GetAll(string applicationId)
    {
        return Ok(_flagService.GetAllForApplication(applicationId));
    }

    [HttpGet("{flagKey}")]
    [ProducesResponseType(typeof(Flag), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public IActionResult GetByKey(string applicationId, string flagKey)
    {
        var flag = _flagService.GetByKey(applicationId, flagKey);
        return flag is null ? NotFound() : Ok(flag);
    }

    [HttpPost]
    [ProducesResponseType(typeof(Flag), StatusCodes.Status201Created)]
    [ProducesResponseType(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status409Conflict)]
    public async Task<IActionResult> Create(string applicationId, [FromBody] Flag flag)
    {
        var created = await _flagService.CreateAsync(applicationId, flag);
        return CreatedAtAction(nameof(GetByKey), new { applicationId, flagKey = created.FlagKey }, created);
    }

    [HttpPut("{flagKey}")]
    [ProducesResponseType(typeof(Flag), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> Update(string applicationId, string flagKey, [FromBody] Flag flag)
    {
        var updated = await _flagService.UpdateAsync(applicationId, flagKey, flag);
        return updated is null ? NotFound() : Ok(updated);
    }

    [HttpDelete("{flagKey}")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> Delete(string applicationId, string flagKey)
    {
        var deleted = await _flagService.DeleteAsync(applicationId, flagKey);
        return deleted ? NoContent() : NotFound();
    }
}
