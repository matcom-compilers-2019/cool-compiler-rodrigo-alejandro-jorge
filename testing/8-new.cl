class Main inherits IO{
    main():Object
    {
        let a : A <- new A in if a.f() then out_string("Jesus!!") else out_string("Christ!!") fi
    };
};

class A{
    a: Int <- 5;
    b: B;

    f() : Bool { isvoid b };
};

class B{
    
};