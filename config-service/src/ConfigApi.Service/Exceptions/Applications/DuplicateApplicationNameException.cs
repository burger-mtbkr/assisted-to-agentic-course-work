namespace ConfigApi.Service.Exceptions.Applications;

public class DuplicateApplicationNameException : Exception
{
    public DuplicateApplicationNameException(string message)
        : base(message)
    {
    }
}
