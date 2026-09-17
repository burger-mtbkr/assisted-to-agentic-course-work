namespace ConfigApi.Service.Exceptions.Applications;

public class ApplicationNotFoundException : Exception
{
    public ApplicationNotFoundException(string message)
        : base(message)
    {
    }
}
