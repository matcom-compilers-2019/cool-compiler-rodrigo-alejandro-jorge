class A inherits IO {
    identify():Object{out_string("I'm of type A!")};
};

class B inherits A {
    identify():Object{out_string("I'm of type B!")};
};

class Main inherits IO {
    main() : Object {
        {
            let me : A <- new A in me@A.identify();
            out_string(" ");

            let me : A <- new B in me@A.identify();
            out_string(" ");

            let me : B <- new B in {
                me@A.identify();
                out_string(" ");
                me@B.identify();
                out_string(" ");
            };
        }
    };
};
