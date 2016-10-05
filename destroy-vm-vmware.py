from pysphere import * 
from pysphere.resources import VimService_services as VI 
from pysphere.vi_task import VITask 

vm_name = "fabian-test.tux.cmcd.local"

#Connect to the server 
s = VIServer() 
s.connect("man-ms018.recon.man", "b-fvdhoeven", "Feyenoord4ever!") 

#Get VM 
vm = s.get_vm_by_name(vm_name) 

#power down VM
#vm.power_off()
#Invoke Destroy_Task 
request = VI.Destroy_TaskRequestMsg() 
_this = request.new__this(vm._mor) 
_this.set_attribute_type(vm._mor.get_attribute_type()) 
request.set_element__this(_this) 
ret = s._proxy.Destroy_Task(request)._returnval 

#Wait for the task to finish 
task = VITask(ret, s) 

status = task.wait_for_state([task.STATE_SUCCESS, task.STATE_ERROR]) 
if status == task.STATE_SUCCESS: 
    print "VM successfully deleted from disk" 
elif status == task.STATE_ERROR: 
    print "Error removing vm:", task.get_error_message() 

#Disconnect from the server 
s.disconnect() 
