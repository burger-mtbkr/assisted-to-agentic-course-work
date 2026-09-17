namespace ConfigApi.Service.Exceptions.Common;

public class ValidationException : Exception
{
    public IReadOnlyDictionary<string, string> Errors { get; }

    public ValidationException(string message, IReadOnlyDictionary<string, string> errors)
        : base(message)
    {
        Errors = errors;
    }
}
