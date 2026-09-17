using Microsoft.AspNetCore.Mvc;

namespace ConfigApi.Service.Controllers.Applications;

[ApiController]
[Route("api/v1/applications")]
public class ApplicationsController : ControllerBase
{
    private readonly IApplicationService _applicationService;

    public ApplicationsController(IApplicationService applicationService)
    {
        _applicationService = applicationService;
    }

    [HttpGet]
    [ProducesResponseType(typeof(IReadOnlyList<Application>), StatusCodes.Status200OK)]
    public IActionResult GetAll()
    {
        return Ok(_applicationService.GetAll());
    }

    [HttpGet("{id}")]
    [ProducesResponseType(typeof(Application), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public IActionResult GetById(string id)
    {
        var application = _applicationService.GetById(id);
        return application is null ? NotFound() : Ok(application);
    }

    [HttpPost]
    [ProducesResponseType(typeof(Application), StatusCodes.Status201Created)]
    [ProducesResponseType(StatusCodes.Status409Conflict)]
    public async Task<IActionResult> Create([FromBody] Application application)
    {
        var created = await _applicationService.CreateAsync(application);
        return CreatedAtAction(nameof(GetById), new { id = created.Id }, created);
    }

    [HttpPut("{id}")]
    [ProducesResponseType(typeof(Application), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<IActionResult> Update(string id, [FromBody] Application application)
    {
        var updated = await _applicationService.UpdateAsync(id, application);
        return updated is null ? NotFound() : Ok(updated);
    }

    [HttpDelete("{id}")]
    [ProducesResponseType(StatusCodes.Status204NoContent)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    [ProducesResponseType(StatusCodes.Status409Conflict)]
    public async Task<IActionResult> Delete(string id)
    {
        var result = await _applicationService.DeleteAsync(id);
        return result switch
        {
            null => NotFound(),
            false => Conflict(),
            true => NoContent()
        };
    }
}
