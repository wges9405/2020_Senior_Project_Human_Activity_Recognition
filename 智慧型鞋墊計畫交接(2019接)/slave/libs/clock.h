bool watch;
unsigned long masterClock = 0;         // counts rising edge clock signals

//ISR function
void clockCounter(){     // called by interrupt
    masterClock++;        // with each clock rise add 1 to masterclock count
    return;
}

class Clock{
    public:
        void startClock(byte hr, byte minute, byte sec) // start timer
        {
            watch = true;
            analogWrite(11, 127);   // this starts our PWM 'clock' with a 50% duty cycle
	    }

        void stopClock() // stop timer
        {
            analogWrite(6, 0);   // stop PWM clock
            watch = false;
        }
};
