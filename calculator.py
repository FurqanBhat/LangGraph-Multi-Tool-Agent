from langchain_core.tools import tool

@tool
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    """
    Perfom a basic arithmetic operation on two numbers.
    Supported operations: add, sub, mul, div
    """

    try:
        if operation == 'add':
            result = first_num + second_num
        elif operation == 'sub':
            result = first_num - second_num
        elif operation == 'mul':
            result = first_num * second_num
        elif operation == 'div':
            if second_num==0:
                result = 'Error: Cannot divide by zero.'
            else:
                result = first_num / second_num
        else:
            return {'Error:' f"Unsupported operstion '{operation}'"}
        return {'first_num':first_num, 'second_num':second_num, 'operation':operation, 'result':result}
    except Exception as e:
        return {"Error": str(e)}
    
