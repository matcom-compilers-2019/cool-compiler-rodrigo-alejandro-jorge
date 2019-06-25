class Main inherits IO {
    main() : Object {
        let a: String <- "Ale", b: String <- "Jorge" in {
        	out_int(a.length());
        	out_string("   ");
        	out_int(b.length());
        	out_string("   ");
        	out_string(a.concat(b));
        	out_string("   ");
        	out_string(a.substr(1,2));
        	out_string("   ");
        }
    };
};
