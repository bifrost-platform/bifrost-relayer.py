# chainpy: web3 library for multichain

### what's difference with web3.py
- 각 Chain data를 간편하게 다룰 수 있는 class 지원 (e.g., EthBlock, EthTransactionType2, EthReceipt)  
- 최소 기능을 갖는 기능별 handler, manager 지원 (e.g., EthRpcClient, TxHandler, EthChainManager, MultiChainManager)  
- 여러 체인과 상호작용하는 single manager 지원  
### MultiChainManager: Interaction to MultiChains
- ChainIndex로 구별하여 rpc, send, call, event monitoring 가능   
- 같은 이름의 event를 여러 chain에서 monitoring 가능
- see "chainpy.eth.managers.multichainmanager.MultiChainManager"
### Advanced "Autotask" Package
the Autotask has two main components: World Monitor and World Task Manager  
##### Multichain Event Monitor
``` python
def run_world_chain_monitor(self):
    """
    A runner to find the designated event from blockchains. Whenever detecting the event, enqueue it.
    """
    while True:  
        # collect unchecked event from all supported chains
        events = self.collect_unchecked_multichain_events()
        for event in events:
            # find type of the detected event 
            event_name = event.event_name
            event_type = self.__events_types[event_name]
            # initiate event to the object  
            chain_event = event_type.from_tuple(event.decoded_data, timestamp_msec())
            # enqueue the obeject of event. the item in the queue will be poped by relayer 
            self.__queue.enqueue(chain_event)

            monitor_logger.info("{} chain event detected".format(chain_event.summary()))
            time.sleep(self.__class__.CHAIN_MONITOR_PERIOD_SEC)
```
##### Support More Complex Task
``` python
def run_multichain_relayer(self):
    """
    A runner to send transaction according to types of specific events.
    """
    while True:
        event: EventABC = self.queue.pop_matured_event()
        if event is None:
            continue

        if isinstance(event, CallAfter):
            # execute call task
            updated_event = self._handle_call_event(event)
            self.queue.enqueue(updated_event)

        elif isinstance(event, EventABC):
            # check the event has been sent before as a transaction.
            handled = True if event.receipt_params is not None else False
            if not handled:
                # send transaction and set "receipt_params" in self._handler_send_event method
                updated_event = self._handle_send_event(event)
                self.queue.enqueue(updated_event)
            else:
                # check transaction receipt using "receipt_params" of the event
                updated_event = self._handle_receipt_event(event)
                self.queue.enqueue(updated_event)
```

##### Register Event Spec
처리할 event에 대한 task는 EventABC를 상속하는 Class로 구현되어야 하고, 사전에 등록되어야 한다. 
``` python
def register_event_type(self, event_name: str, event_type: type):
    if not issubclass(event_type, EventABC):
        raise Exception("event type to be registered must subclass of EventABC")
    if event_name in self.__events_types.keys():
        raise Exception("Already existing type: {}".format(event_type))
        self.__events_types[event_name] = event_type
```
##### Abstract class for the specific event (EventABC class)
event data를 저장하는 tuple 멤버로 갖는다. (from_tuple(tuple), tuple() -> tuple)  
개발자는 다음과 같은 abstractmethod를 구현해야 한다.
```text
- summary: event를 표현하는 string 출력, logging에 사용됨
- build_transaction: event 감지시 전송될 tx을 생성한다. (자동 호출됨)
- handle_success_event: tx 전송 성공(receipt status == 1)시 수행될 작업을 명시함 (자동 호출됨)
- handle_fail_event: tx 전송 실패(estimate fails)시 수행될 작업을 명시함 (자동 호출됨)
- handle_no_receipt_event: tx의 receipt이 발견되지 않으면 수행될 작업을 명시함 (미구현)
- bootstrap: 부팅 시 일괄 수집된 legacy events를 처리한다. Task로서 처리할 event를 리턴해야 한다. (자동 호출됨)
```
단, summary, build_transaction, handle_success_event만 구현하면 기존 autotask와 동일하게 사용할 수 있음.

### Example1
Goerli의 contract에서 발생한 Event는 Spolia의 contract로 전송하고,  
반대로 Spolia의 contract에서 발생한 Event는 Goerli의 contract로 전송하는 예제는 다음과 같이 구현될 수 있다.  
문제점: autotask의 tx로 target event가 발생하여, autotask는 무한히 relay를 하게 된다.

```python
class SetterEvent(EventABC):
    def summary(self) -> str:
        return "{}:{}".format(self.__class__.__name__, self.data)

    def build_transaction(self, *args) -> tuple:
        dst_chain = ChainIndex.SPOLIA if self.on_chain == ChainIndex.GOERLI else ChainIndex.GOERLI
        contract = "lottery"
        method = "setValue"
        params = [self.data[0]]
        self.x = print(params)

        return dst_chain, contract, method, params

    def handle_success_event(self, *args):
        pass

    def handle_no_receipt_event(self, *args):
        pass

    def handle_fail_event(self, *args):
        pass

    @staticmethod
    def bootstrap(detected_event: List[DetectedEvent], ranges: Dict[ChainIndex, Tuple[int, int]]) -> List['EventABC']:
        pass


if __name__ == "__main__":
    auto_task = AutoTask.from_config_dict(entity_root_config_dict)
    auto_task.register_chain_event_obj("TestEvent", SetterEvent)
    auto_task.run_eventbridge()
```

### Example2
Example1을 개선하여 양쪽 contract가 서로 같은 값을 가지고 있으면 autotask가 relay 하지 않도록 수정함.

```python
class SetterEventExample2(EventABC):
    def summary(self) -> str:
        return "{}:{}".format(self.__class__.__name__, self.data)

    def build_transaction(self, *args) -> tuple:
        dst_chain = ChainIndex.SPOLIA if self.on_chain == ChainIndex.GOERLI else ChainIndex.GOERLI
        chain_config_dict = spolia_chain_config_dict if self.on_chain == ChainIndex.GOERLI else goerli_chain_config_dict
        chain_manager = EthChainManager.from_config_dict(dst_chain, chain_config_dict)

        contract = "lottery"
        # call and check contract's value
        call_method, call_params = "getValue", []
        result = chain_manager.eth_call(contract, call_method, call_params)

        # conditional send "setValue" transaction
        send_method = "setValue"
        if self.data[0] != result[0]:
            return dst_chain, contract, send_method, [self.data[0]]
        else:
            return ChainIndex.NONE, "", "", []

    def handle_success_event(self, *args):
        pass

    def handle_no_receipt_event(self, *args):
        pass

    def handle_fail_event(self, *args):
        pass

    @staticmethod
    def bootstrap(detected_event: List[DetectedEvent], ranges: Dict[ChainIndex, Tuple[int, int]]) -> List['EventABC']:
        pass
```


### Testing and Interface
```
# test managers
$ pip install -r requirement.txt
$ cd chainpy
$ export PYTHONPATH=`pwd -P`
$ python chainpy/eth/managers/test_managers.py
```

```
# autotask example
$ pip install -r requirement.txt
$ cd chainpy
$ export PYTHONPATH=`pwd -P`
$ python chainpy/autotask/test_autotask.py
```
