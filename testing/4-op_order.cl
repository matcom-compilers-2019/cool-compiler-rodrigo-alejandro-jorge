class Main inherits IO{
    main():Object
    {
        let a : Int <- 2, b : Int <- 3, c : Int <- 4, d : Int <- 2 in 
        {
            out_int(a*b+c*d);-- 14
            out_string(" ");
            out_int(a/(b-c)/d);-- -1
        }
    };
};