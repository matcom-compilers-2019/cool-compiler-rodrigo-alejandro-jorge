class A inherits IO {
    x: Int;
    b: B <- new B;

    set_x(n_x: Int) : Object{
        x <- n_x
    };
    set_bx(n_bb: Int) : Object{
        b.set_x(n_bb)
    };
    print_x(): Object{
        out_int(x)
    };
    print_bx(): Object{
        b.print_x()
    };
};

class B inherits IO{
    x: Int;

    set_x(n_x: Int) : Object{
        x <- n_x
    };
    print_x(): Object{
        out_int(x)
    };
};

class Main inherits IO {
    main() : Object {
        let a: A <- new A, a_prima: A <- a.copy() in {
            a_prima.set_x(5); 
            a_prima.set_bx(5); 

            out_string("(1)");
            a.print_x();
            out_string("(2)");
            a_prima.print_x();
            out_string("(3)"); 
            a.print_bx(); 
            out_string("(4)");
            a_prima.print_bx();
            abort();
        }
    };
};
