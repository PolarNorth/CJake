# This script should be used in the compiled java standard library directory and will produce headers needed for the JVM

cd bin

javah java.lang.Class
javah java.lang.ClassLoader
javah java.lang.Compiler
javah java.lang.Double
# javah java.lang.fdlib
javah java.lang.Float
# javah java.lang.java_props
javah java.lang.Object
javah java.lang.Package
javah java.lang.reflect.Array
javah java.lang.reflect.Executable
javah java.lang.reflect.Field
javah java.lang.reflect.Proxy
javah java.lang.Runtime
javah java.lang.SecurityManager
javah java.lang.Shutdown
javah java.lang.StrictMath
javah java.lang.String
javah java.lang.System
javah java.lang.Thread
javah java.lang.Throwable
