class Main inherits IO {
    main() : Object {
        {
        	out_string(5.type_name());
        	out_string(f(5));
        	let x:Object <-5 in out_string(x.type_name());
        	let y:Int <- 5.copy() + 5 in out_int(y);
    	}


    };
    f(x: Object) :String{
        x.type_name()
    };
};
